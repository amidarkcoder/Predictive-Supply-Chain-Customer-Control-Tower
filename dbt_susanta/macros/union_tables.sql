{% macro union_tables(schema_name, table_list) %}
    {%- for table in table_list %}
select * from {{ schema_name }}.`{{ table }}`
        {%- if not loop.last %}
union all
        {%- endif %}
    {%- endfor %}
{% endmacro %}
