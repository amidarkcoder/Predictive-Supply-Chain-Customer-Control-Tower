{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key=['snapshot_date', 'warehouse_id', 'sku_id'],
        partition_by=['snapshot_date'],
        on_schema_change='sync_all_columns'
    )
}}

with source_inventory as (
    select
        snapshot_date,
        warehouse_id,
        sku_id,
        on_hand_qty,
        safety_stock,
        lead_time,
        rop,
        last_supply_date,
        holding_cost,

        datediff(snapshot_date, last_supply_date) as days_since_last_supply,
        round(on_hand_qty * holding_cost, 2) as total_holding_cost,
        case when on_hand_qty = 0 then 1 else 0 end as is_stockout,
        case when on_hand_qty <= rop then 1 else 0 end as is_below_rop,
        case when on_hand_qty < safety_stock then 1 else 0 end as is_below_safety_stock,
        current_timestamp() as dbt_updated_at

    from {{ source('silver', 'inventory_2025_all') }}

    {% if is_incremental() %}
        where snapshot_date >= (
            select date_sub(max(snapshot_date), 3) from {{ this }}
        )
    {% endif %}
)

select * from source_inventory
