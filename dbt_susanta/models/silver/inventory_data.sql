select *
from {{ source('silver','inventory_2025_all') }}