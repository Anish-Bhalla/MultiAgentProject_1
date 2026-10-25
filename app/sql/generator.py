"""Optional LLM SQL generation with deterministic fallbacks for no-key demo mode."""
from __future__ import annotations
import json
import re
from app.config import get_settings
from app.llm import get_llm

SCHEMA_TEXT = """
customers(customer_id, customer_name, region)
products(product_id, product_name, category, list_price)
orders(order_id, customer_id, order_date, status, region)
order_items(item_id, order_id, product_id, quantity, unit_price, discount_pct)
Revenue = SUM(order_items.quantity * order_items.unit_price * (1 - order_items.discount_pct)).
Use only completed orders unless the user explicitly requests another status. Dates are ISO YYYY-MM-DD.
""".strip()


def heuristic_sql(question: str) -> str:
    q = question.lower()
    limit_match = re.search(r"\btop\s+(\d{1,2})\b", q)
    limit = min(int(limit_match.group(1)), 50) if limit_match else 5
    if "region" in q or "regional" in q:
        return """SELECT o.region, ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct)), 2) AS revenue
FROM orders o JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.status = 'completed' GROUP BY o.region ORDER BY revenue DESC LIMIT 50"""
    if "customer" in q and any(word in q for word in ("top", "highest", "spend", "revenue", "sales")):
        return f"""SELECT c.customer_name, ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct)), 2) AS revenue
FROM customers c JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.status = 'completed' GROUP BY c.customer_id, c.customer_name ORDER BY revenue DESC LIMIT {limit}"""
    if "quarter" in q or "quarterly" in q:
        return """SELECT strftime('%Y', o.order_date) || '-Q' || CAST(((CAST(strftime('%m', o.order_date) AS INTEGER)-1)/3)+1 AS INTEGER) AS quarter,
ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct)), 2) AS revenue
FROM orders o JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.status = 'completed' GROUP BY quarter ORDER BY quarter"""
    if "category" in q or "categories" in q:
        return """SELECT p.category, ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct)), 2) AS revenue
FROM products p JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o ON o.order_id = oi.order_id WHERE o.status = 'completed'
GROUP BY p.category ORDER BY revenue DESC LIMIT 50"""
    if "product" in q or "item" in q or "best-selling" in q or "best selling" in q:
        return f"""SELECT p.product_name, ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct)), 2) AS revenue
FROM products p JOIN order_items oi ON p.product_id = oi.product_id
JOIN orders o ON o.order_id = oi.order_id WHERE o.status = 'completed'
GROUP BY p.product_id, p.product_name ORDER BY revenue DESC LIMIT {limit}"""
    if "count" in q and "order" in q:
        return "SELECT status, COUNT(*) AS order_count FROM orders GROUP BY status ORDER BY order_count DESC"
    if "revenue" in q or "sales" in q or "total" in q:
        return """SELECT ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct)), 2) AS total_revenue
FROM orders o JOIN order_items oi ON o.order_id = oi.order_id WHERE o.status = 'completed'"""
    return """SELECT p.product_name, ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_pct)), 2) AS revenue
FROM products p JOIN order_items oi ON p.product_id = oi.product_id JOIN orders o ON o.order_id = oi.order_id
WHERE o.status = 'completed' GROUP BY p.product_id, p.product_name ORDER BY revenue DESC LIMIT 5"""


async def generate_sql(question: str) -> tuple[str, str]:
    llm = get_llm()
    if llm is None:
        return heuristic_sql(question), "heuristic_demo_mode"
    prompt = (
        "Convert the user's question into exactly one SQLite SELECT query. Never write or modify data. "
        "Use only tables/columns in the supplied schema. Use aliases for aggregates. Return SQL only, no markdown.\n\n"
        f"Schema:\n{SCHEMA_TEXT}\n\nQuestion: {question}"
    )
    try:
        result = await llm.ainvoke(prompt)
        sql = str(result.content).strip()
        sql = re.sub(r"^```(?:sql)?\s*|\s*```$", "", sql, flags=re.IGNORECASE)
        return sql, "llm"
    except Exception:
        # Keep the demonstration usable during provider outages; the SQL still
        # passes through the same AST validator and read-only executor.
        return heuristic_sql(question), "heuristic_fallback_after_llm_error"
