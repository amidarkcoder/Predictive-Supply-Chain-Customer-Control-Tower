{% macro copy_schema_tables(source_schema, target_schema) %}
    
    {% do run_query("CREATE SCHEMA IF NOT EXISTS " ~ target_schema) %}

    {% set get_tables_query %}
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = '{{ source_schema }}'
          AND table_type != 'VIEW'
    {% endset %}

    {% set results = run_query(get_tables_query) %}

    {% if execute %}
        {% set table_list = results.columns[0].values() %}
        
        {% for table_name in table_list %}
            {{ log("Copying " ~ source_schema ~ "." ~ table_name ~ " to " ~ target_schema ~ "." ~ table_name, info=True) }}
            
            {% set copy_sql %}
                CREATE OR REPLACE TABLE {{ target_schema }}.`{{ table_name }}` AS
                SELECT * FROM {{ source_schema }}.`{{ table_name }}`
            {% endset %}
            
            {% do run_query(copy_sql) %}
        {% endfor %}
    {% endif %}

{% endmacro %}
 