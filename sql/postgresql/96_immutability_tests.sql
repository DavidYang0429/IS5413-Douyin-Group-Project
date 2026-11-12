DO $tests$
DECLARE r record; code text; outcomes jsonb:='[]'::jsonb;
BEGIN
FOR r IN SELECT * FROM (VALUES
('self_parent','INSERT INTO douyin."COMMENT" (comment_id,video_id,author_id,parent_comment_id,body_text) VALUES (900001,1,1,900001,''bad'')'),
('immutable_comment_ancestry','UPDATE douyin."COMMENT" SET parent_comment_id=3 WHERE comment_id=1'),
('immutable_video_creator','UPDATE douyin."VIDEO" SET creator_id=2 WHERE video_id=1'),
('immutable_collection_owner','UPDATE douyin."COLLECTION" SET owner_id=2 WHERE collection_id=1')
) x(name,sql) LOOP
 BEGIN EXECUTE r.sql; RAISE EXCEPTION USING ERRCODE='ZX001'; EXCEPTION WHEN OTHERS THEN GET STACKED DIAGNOSTICS code=RETURNED_SQLSTATE; END;
 IF code<>'23514' THEN RAISE EXCEPTION 'Guard % failed with %',r.name,code; END IF;
 outcomes:=outcomes||jsonb_build_array(jsonb_build_object('test',r.name,'passed',true,'sqlstate',code));
END LOOP;
PERFORM set_config('douyin.admin_guard_results',outcomes::text,false);
END $tests$;
SELECT current_setting('douyin.admin_guard_results')::jsonb AS guard_tests;
