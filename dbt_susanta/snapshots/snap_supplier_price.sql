{% snapshot snap_supplier_price %}

{{
    config(
        target_schema='snapshots',
        unique_key="concat(supplier_id, '-', sku_id)",
        strategy='check',
        check_cols=['unit_price', 'discount'],
        updated_at='updated_at',
        invalidate_hard_deletes=True
    )
}}

select
    concat(supplier_id, '-', sku_id) as supplier_sku_sk,
    supplier_id,
    sku_id,
    supplier_name,
    location,
    unit_price,
    discount,
    round(unit_price * (1 - coalesce(discount, 0)), 2) as net_unit_price,
    updated_at
from {{ ref('supplier') }}

{% endsnapshot %}
