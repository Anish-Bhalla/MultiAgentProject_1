from app.sql.demo_database import init_business_db
from app.sql.executor import execute_readonly_sql, get_schema


def test_demo_db_is_queryable_and_read_only():
    init_business_db()
    schema = get_schema()
    assert "orders" in schema and "order_items" in schema
    result = execute_readonly_sql("SELECT COUNT(*) AS n FROM orders")
    assert result["row_count"] == 1
    assert result["rows"][0]["n"] > 0
    assert result["read_only"] is True
