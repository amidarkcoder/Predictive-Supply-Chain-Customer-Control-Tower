{{ config(
    materialized='table',
    schema='silver'
) }}

{% set source_schema = "bronze" %}
{% set tables = [
    "orders_2025-01",
    "orders_2025-02",
    "orders_2025-03",
    "orders_2025-04",
    "orders_2025-05",
    "orders_2025-06"
] %}

{{ union_tables(source_schema, tables) }}