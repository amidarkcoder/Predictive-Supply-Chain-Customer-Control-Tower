{{ config(
    materialized='table',
    schema='silver'
) }}

{% set source_schema = "bronze" %}
{% set tables = [
    "inventory_2025-01",
    "inventory_2025-02",
    "inventory_2025-03",
    "inventory_2025-04",
    "inventory_2025-05",
    "inventory_2025-06"
] %}

{{ union_tables(source_schema, tables) }}
