{{
    config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key=['order_id', 'sku_id'],
        partition_by=['order_date'],
        on_schema_change='sync_all_columns'
    )
}}

with source_orders as (
    select
        order_id,
        sku_id,
        warehouse_id,
        customer_id,
        delivery_partner_id,
        order_date,
        dispatch_date,
        delivered_date,
        promised_date,
        order_status,
        quantity,
        unit_price,
        discount_pct,
        amount as net_amount,
        shipping_cost,
        sku_rating,

        datediff(dispatch_date, order_date) as days_to_dispatch,
        datediff(delivered_date, dispatch_date) as transit_days,
        datediff(delivered_date, order_date) as total_delivery_days,
        case
            when delivered_date is not null and promised_date is not null and delivered_date > promised_date then 1
            when delivered_date is null and promised_date is not null and current_date() > promised_date then 1
            else 0
        end as is_sla_breached,
        current_timestamp() as dbt_updated_at

    from {{ source('silver', 'order_2025_all') }}

    {% if is_incremental() %}
        where order_date >= (
            select date_sub(max(order_date), 14) from {{ this }}
        )
    {% endif %}
)

select * from source_orders
