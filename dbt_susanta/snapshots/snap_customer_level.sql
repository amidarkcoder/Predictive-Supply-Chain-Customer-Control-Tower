{% snapshot snap_customer_level %}

{{
    config(
        target_schema='snapshots',
        unique_key='customer_id',
        strategy='check',
        check_cols=['customer_level'],
        updated_at='updated_at',
        invalidate_hard_deletes=True
    )
}}

select
    customer_id,
    name,
    location,
    signup_date,
    customer_level,
    updated_at
from {{ ref('customer') }}

{% endsnapshot %}
