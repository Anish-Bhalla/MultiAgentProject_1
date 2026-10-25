import pytest
from app.sql.validator import SQLSafetyError, validate_select_sql


def test_simple_select_is_allowed():
    sql = validate_select_sql("SELECT product_name FROM products LIMIT 5")
    assert "SELECT" in sql.upper()


def test_select_with_join_is_allowed():
    sql = validate_select_sql("SELECT p.product_name FROM products p JOIN order_items oi ON p.product_id = oi.product_id")
    assert "JOIN" in sql.upper()


@pytest.mark.parametrize("sql", [
    "DELETE FROM orders",
    "DROP TABLE products",
    "SELECT * FROM customers; DELETE FROM customers",
    "SELECT * FROM sqlite_master",
    "SELECT * FROM payroll",
    "PRAGMA table_info(orders)",
])
def test_unsafe_or_unapproved_sql_is_blocked(sql):
    with pytest.raises(SQLSafetyError):
        validate_select_sql(sql)
