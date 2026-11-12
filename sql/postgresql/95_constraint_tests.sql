-- Structural constraint acceptance against 02_seed.sql fixtures.
-- Every probe runs in an exception subtransaction; successful probes are rolled back.
-- No existing row is deleted or changed. Explicit probe IDs avoid advancing identities.
-- This does NOT test business authorization, concurrency or hidden-video writes.
DO $verify$
DECLARE
    test record;
    actual_state text;
    actual_constraint text;
    results jsonb := '[]'::jsonb;
BEGIN
    FOR test IN SELECT * FROM (VALUES
        ('duplicate_phone', 'INSERT INTO douyin."USER" (user_id,phone,nickname) VALUES (90001,''+19990000001'',''Test'')', '23505'),
        ('blank_phone', 'INSERT INTO douyin."USER" (user_id,phone,nickname) VALUES (90001,''   '',''Test'')', '23514'),
        ('non_ascii_phone', 'INSERT INTO douyin."USER" (user_id,phone,nickname) VALUES (90001,''１２３'',''Test'')', '23514'),
        ('invalid_account_status', 'INSERT INTO douyin."USER" (user_id,phone,nickname,account_status) VALUES (90001,''+19999999999'',''Test'',''UNKNOWN'')', '23514'),
        ('negative_identity', 'INSERT INTO douyin."USER" (user_id,phone,nickname) VALUES (-1,''+19999999999'',''Test'')', '23514'),
        ('duplicate_topic', 'INSERT INTO douyin."TOPIC" (topic_id,topic_name) VALUES (90001,''SQL'')', '23505'),
        ('blank_topic', 'INSERT INTO douyin."TOPIC" (topic_id,topic_name) VALUES (90001,'' '')', '23514'),
        ('padded_topic', 'INSERT INTO douyin."TOPIC" (topic_id,topic_name) VALUES (90001,'' SQL '')', '23514'),
        ('zero_duration', 'INSERT INTO douyin."VIDEO" (video_id,creator_id,media_url,duration_seconds,visibility_status) VALUES (90001,1,''https://example.invalid/test.mp4'',0,''PUBLISHED'')', '23514'),
        ('orphan_creator', 'INSERT INTO douyin."VIDEO" (video_id,creator_id,media_url,duration_seconds,visibility_status) VALUES (90001,99999,''https://example.invalid/test.mp4'',1,''PUBLISHED'')', '23503'),
        ('invalid_video_status', 'INSERT INTO douyin."VIDEO" (video_id,creator_id,media_url,duration_seconds,visibility_status) VALUES (90001,1,''https://example.invalid/test.mp4'',1,''DRAFT'')', '23514'),
        ('null_video_url', 'INSERT INTO douyin."VIDEO" (video_id,creator_id,media_url,duration_seconds) VALUES (90001,1,NULL,1)', '23502'),
        ('orphan_parent_comment', 'INSERT INTO douyin."COMMENT" (comment_id,video_id,author_id,parent_comment_id,body_text) VALUES (90001,1,1,99999,''Test'')', '23503'),
        ('blank_comment', 'INSERT INTO douyin."COMMENT" (comment_id,video_id,author_id,body_text) VALUES (90001,1,1,''   '')', '23514'),
        ('null_comment_body', 'INSERT INTO douyin."COMMENT" (comment_id,video_id,author_id,body_text) VALUES (90001,1,1,NULL)', '23502'),
        ('invalid_comment_status', 'INSERT INTO douyin."COMMENT" (comment_id,video_id,author_id,body_text,comment_status) VALUES (90001,1,1,''Test'',''UNKNOWN'')', '23514'),
        ('duplicate_video_topic', 'INSERT INTO douyin."VIDEO_TOPIC" (video_id,topic_id) VALUES (1,1)', '23505'),
        ('duplicate_like', 'INSERT INTO douyin."VIDEO_LIKE" (user_id,video_id) VALUES (1,1)', '23505'),
        ('orphan_like_video', 'INSERT INTO douyin."VIDEO_LIKE" (user_id,video_id) VALUES (1,99999)', '23503'),
        ('duplicate_follow', 'INSERT INTO douyin."FOLLOW" (follower_id,followed_id) VALUES (1,2)', '23505'),
        ('self_follow', 'INSERT INTO douyin."FOLLOW" (follower_id,followed_id) VALUES (1,1)', '23514'),
        ('duplicate_collection_name_for_owner', 'INSERT INTO douyin."COLLECTION" (collection_id,owner_id,collection_name) VALUES (90001,1,''Study'')', '23505'),
        ('blank_collection_name', 'INSERT INTO douyin."COLLECTION" (collection_id,owner_id,collection_name) VALUES (90001,1,'' '')', '23514'),
        ('duplicate_video_within_collection', 'INSERT INTO douyin."COLLECTION_ITEM" (collection_id,item_no,video_id) VALUES (1,999,1)', '23505'),
        ('zero_local_item_number', 'INSERT INTO douyin."COLLECTION_ITEM" (collection_id,item_no,video_id) VALUES (1,0,2)', '23514'),
        ('non_unique_nickname_allowed', 'INSERT INTO douyin."USER" (user_id,phone,nickname) VALUES (90001,''+19999999999'',''Demo_Ada'')', NULL),
        ('no_music_and_empty_caption_allowed', 'INSERT INTO douyin."VIDEO" (video_id,creator_id,media_url,duration_seconds,visibility_status) VALUES (90001,1,''https://example.invalid/test.mp4'',1,''PUBLISHED'')', NULL),
        ('case_distinct_topic_allowed', 'INSERT INTO douyin."TOPIC" (topic_id,topic_name) VALUES (90001,''sql'')', NULL),
        ('same_collection_name_different_owner_allowed', 'INSERT INTO douyin."COLLECTION" (collection_id,owner_id,collection_name) VALUES (90001,3,''Study'')', NULL),
        ('self_like_allowed', 'INSERT INTO douyin."VIDEO_LIKE" (user_id,video_id) VALUES (3,5)', NULL),
        ('same_video_in_different_collection_allowed', 'INSERT INTO douyin."COLLECTION_ITEM" (collection_id,item_no,video_id) VALUES (3,2,1)', NULL)
    ) AS cases(test_name, statement_sql, expected_state) LOOP
        actual_state := NULL;
        actual_constraint := NULL;
        BEGIN
            EXECUTE test.statement_sql;
            -- Roll back even an unexpectedly accepted negative probe.
            RAISE EXCEPTION USING ERRCODE = 'ZX001', MESSAGE = 'rollback successful probe';
        EXCEPTION WHEN OTHERS THEN
            GET STACKED DIAGNOSTICS actual_state = RETURNED_SQLSTATE,
                                    actual_constraint = CONSTRAINT_NAME;
        END;
        IF (test.expected_state IS NULL AND actual_state = 'ZX001')
           OR (test.expected_state IS NOT NULL AND actual_state = test.expected_state) THEN
            results := results || jsonb_build_array(jsonb_build_object(
                'test', test.test_name, 'passed', true,
                'expected', COALESCE(test.expected_state, 'ACCEPT'),
                'actual', CASE WHEN actual_state = 'ZX001' THEN 'ACCEPT' ELSE actual_state END,
                'constraint', actual_constraint));
        ELSE
            RAISE EXCEPTION 'Test % failed: expected %, received %',
                test.test_name, COALESCE(test.expected_state, 'ACCEPT'), actual_state;
        END IF;
    END LOOP;
    PERFORM set_config('douyin.validation_results', results::text, false);
END;
$verify$;
SELECT current_setting('douyin.validation_results')::jsonb AS constraint_tests;
