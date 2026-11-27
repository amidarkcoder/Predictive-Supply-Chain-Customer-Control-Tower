{% macro copy_table(source_schema, target_schema, table_list) %}
    {%- if execute -%}
        {%- for table in table_list %}
            {% set sql %}
                create or replace table {{ target_schema }}.{{ table }}
                using delta
                as select * from {{ source_schema }}.{{ table }}
            {% endset %}
            {% do run_query(sql) %}
        {%- endfor %}
    {%- endif -%}
{% endmacro %}
