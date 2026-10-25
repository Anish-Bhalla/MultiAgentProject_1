# DEMO DATA ONLY — Business Database Data Dictionary

This document describes the **synthetic sales database** supplied with the portfolio project. It is not an actual company's data.

## Tables

- `customers`: one row per synthetic customer account; includes a coarse region.
- `products`: one row per synthetic product, category, and list price.
- `orders`: order header with order date, status, customer, and region.
- `order_items`: line items with quantity, realized unit price, and a decimal discount fraction.

## Revenue definition

For this demo, gross line revenue after discount is calculated as:

`quantity * unit_price * (1 - discount_pct)`

Unless the user asks otherwise, include only orders whose status is `completed`. This database is generated deterministically for engineering tests. Its results must never be described as real company performance.
