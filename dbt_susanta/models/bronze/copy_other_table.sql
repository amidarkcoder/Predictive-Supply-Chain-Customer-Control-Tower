{{ copy_table(
    source_schema='dbt_adv_pr.bronze',
    target_schema='dbt_adv_pr.silver',
    table_list=[
        'customer',
        'customer_segments',
        'customer_updates',
        'delivery_partner',
        'sku_profile',
        'supplier',
        'supplier_profile',
        'supplier_updates',
        'warehouse'
    ]
) }}

select 1 as status
