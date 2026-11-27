{{ config(
    materialized='table',
    schema='silver'
) }}

{% set source_schema = "bronze" %}
{% set tables = [
    "purchase_orders_2025-01",
    "purchase_orders_2025-02",
    "purchase_orders_2025-03",
    "purchase_orders_2025-04",
    "purchase_orders_2025-05",
    "purchase_orders_2025-06"

] %}

{{ union_tables(source_schema, tables) }}