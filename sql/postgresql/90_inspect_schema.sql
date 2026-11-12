-- Read-only, one JSON result for reproducible catalog and access inspection.
SELECT jsonb_build_object(
    'database', current_database(),
    'server_version', current_setting('server_version'),
    'columns', (
        SELECT jsonb_agg(jsonb_build_object(
            'table', table_name, 'column', column_name, 'position', ordinal_position,
            'type', data_type, 'nullable', is_nullable, 'identity', is_identity,
            'collation', collation_name
        ) ORDER BY table_name, ordinal_position)
        FROM information_schema.columns WHERE table_schema = 'douyin'
    ),
    'constraints', (
        SELECT jsonb_agg(jsonb_build_object(
            'table', t.relname, 'name', c.conname, 'type', c.contype,
            'columns', (SELECT jsonb_agg(a.attname ORDER BY k.ord)
                        FROM unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord)
                        JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum),
            'ref_table', r.relname,
            'ref_columns', (SELECT jsonb_agg(a.attname ORDER BY k.ord)
                            FROM unnest(c.confkey) WITH ORDINALITY AS k(attnum, ord)
                            JOIN pg_attribute a ON a.attrelid = c.confrelid AND a.attnum = k.attnum),
            'definition', pg_get_constraintdef(c.oid), 'validated', c.convalidated
        ) ORDER BY t.relname, c.conname)
        FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = c.connamespace
        LEFT JOIN pg_class r ON r.oid = c.confrelid
        WHERE n.nspname = 'douyin'
    ),
    'tables', (SELECT jsonb_agg(jsonb_build_object('table', tablename, 'rls', rowsecurity) ORDER BY tablename)
               FROM pg_tables WHERE schemaname = 'douyin'),
    'indexes', (SELECT jsonb_agg(jsonb_build_object('table', tablename, 'name', indexname, 'definition', indexdef) ORDER BY tablename, indexname)
                FROM pg_indexes WHERE schemaname = 'douyin'),
    'roles', (SELECT jsonb_agg(jsonb_build_object(
        'role', role_name, 'schema_usage', has_schema_privilege(role_name, 'douyin', 'USAGE'),
        'user_select', has_table_privilege(role_name, 'douyin."USER"', 'SELECT'),
        'user_insert', has_table_privilege(role_name, 'douyin."USER"', 'INSERT')
    )) FROM (VALUES ('anon'), ('authenticated'), ('service_role')) AS roles(role_name)),
    'row_counts', (SELECT jsonb_object_agg(table_name, row_count) FROM (
        SELECT 'USER' AS table_name, count(*) AS row_count FROM douyin."USER"
        UNION ALL SELECT 'MUSIC', count(*) FROM douyin."MUSIC"
        UNION ALL SELECT 'TOPIC', count(*) FROM douyin."TOPIC"
        UNION ALL SELECT 'VIDEO', count(*) FROM douyin."VIDEO"
        UNION ALL SELECT 'COMMENT', count(*) FROM douyin."COMMENT"
        UNION ALL SELECT 'VIDEO_TOPIC', count(*) FROM douyin."VIDEO_TOPIC"
        UNION ALL SELECT 'VIDEO_LIKE', count(*) FROM douyin."VIDEO_LIKE"
        UNION ALL SELECT 'FOLLOW', count(*) FROM douyin."FOLLOW"
        UNION ALL SELECT 'COLLECTION', count(*) FROM douyin."COLLECTION"
        UNION ALL SELECT 'COLLECTION_ITEM', count(*) FROM douyin."COLLECTION_ITEM"
    ) AS counts)
) AS inspection;
