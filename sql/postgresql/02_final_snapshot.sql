-- Exact 100-row synthetic snapshot matching the final report capture.

-- Use INSTEAD OF 02_seed.sql, after 01_schema.sql and BEFORE 04_business_rules.sql.

-- Existing nonempty tables are refused. No password, auth schema or role secret is exported.

BEGIN;

DO $seed_guard$
DECLARE
    t text;
    occupied boolean;
BEGIN
    FOREACH t IN ARRAY ARRAY['USER','MUSIC','TOPIC','VIDEO','COMMENT','VIDEO_TOPIC',
                            'VIDEO_LIKE','FOLLOW','COLLECTION','COLLECTION_ITEM'] LOOP
        EXECUTE format('select exists(select 1 from douyin.%I)', t) INTO occupied;
        IF occupied THEN
            RAISE EXCEPTION 'Snapshot refused: douyin.% already contains data', t;
        END IF;
    END LOOP;
END;
$seed_guard$;



INSERT INTO douyin."USER" (user_id, phone, nickname, account_status, registered_at) VALUES
    (1, '+19990000001', 'Demo_Ada', 'ACTIVE', '2026-11-01T08:00:00+00:00'),
    (2, '+19990000002', 'Demo_Ben', 'ACTIVE', '2026-11-01T08:01:00+00:00'),
    (3, '+19990000003', 'Demo_Chen', 'ACTIVE', '2026-11-01T08:02:00+00:00'),
    (4, '+19990000004', 'Demo_Dina', 'ACTIVE', '2026-11-01T08:03:00+00:00'),
    (5, '+19990000005', 'Demo_Eli', 'ACTIVE', '2026-11-01T08:04:00+00:00'),
    (6, '+19990000006', 'Demo_Faye', 'DISABLED', '2026-11-01T08:05:00+00:00');

INSERT INTO douyin."MUSIC" (music_id, title, artist_name, audio_url) VALUES
    (1, 'Campus Beat', 'Demo Artist A', 'https://example.invalid/audio/campus.mp3'),
    (2, 'Coffee Loop', 'Demo Artist B', 'https://example.invalid/audio/coffee.mp3'),
    (3, 'Practice Track', 'Demo Artist C', 'https://example.invalid/audio/practice.mp3');

INSERT INTO douyin."TOPIC" (topic_id, topic_name) VALUES
    (1, 'Study'),
    (2, 'Life'),
    (3, 'SQL'),
    (4, 'Music'),
    (5, 'Unused');

INSERT INTO douyin."VIDEO" (video_id, creator_id, music_id, caption, media_url, duration_seconds, visibility_status, published_at) VALUES
    (1, 1, 1, 'CityU campus walk', 'https://example.invalid/video/1.mp4', 25.5, 'PUBLISHED', '2026-11-02T09:00:00+00:00'),
    (2, 2, 2, 'Coffee in Hong Kong', 'https://example.invalid/video/2.mp4', 18, 'PUBLISHED', '2026-11-02T10:00:00+00:00'),
    (3, 1, NULL, 'SQL joins explained', 'https://example.invalid/video/3.mp4', 55.125, 'PUBLISHED', '2026-11-03T09:00:00+00:00'),
    (4, 3, 3, 'Hidden rehearsal', 'https://example.invalid/video/4.mp4', 30, 'HIDDEN', '2026-11-03T10:00:00+00:00'),
    (5, 3, NULL, 'Study desk setup', 'https://example.invalid/video/5.mp4', 12.5, 'PUBLISHED', '2026-11-04T09:00:00+00:00'),
    (6, 4, 1, 'Harbour sunset', 'https://example.invalid/video/6.mp4', 40, 'PUBLISHED', '2026-11-04T10:00:00+00:00'),
    (7, 2, NULL, 'An empty interaction example', 'https://example.invalid/video/7.mp4', 10, 'PUBLISHED', '2026-11-05T09:00:00+00:00'),
    (8, 4, NULL, '', 'https://example.invalid/video/8.mp4', 5.25, 'PUBLISHED', '2026-11-05T10:00:00+00:00'),
    (11, 1, NULL, 'Concurrency verification 0', '/media/demo.webm', 3, 'HIDDEN', '2026-11-12T05:49:44.241+00:00'),
    (12, 1, NULL, 'Concurrency verification 1', '/media/demo.webm', 3, 'HIDDEN', '2026-11-12T05:49:44.241+00:00'),
    (13, 1, NULL, 'Concurrency verification 0', '/media/demo.webm', 3, 'HIDDEN', '2026-11-12T05:49:51.071+00:00'),
    (14, 1, NULL, 'Concurrency verification 1', '/media/demo.webm', 3, 'HIDDEN', '2026-11-12T05:49:51.071+00:00'),
    (17, 1, NULL, 'Concurrency verification 0', '/media/demo.webm', 3, 'HIDDEN', '2026-11-12T05:51:19.753+00:00'),
    (18, 1, NULL, 'Concurrency verification 1', '/media/demo.webm', 3, 'HIDDEN', '2026-11-12T05:51:19.753+00:00'),
    (19, 1, NULL, 'Concurrency verification 0', '/media/demo.webm', 3, 'HIDDEN', '2026-11-12T05:51:25.593+00:00'),
    (20, 1, NULL, 'Concurrency verification 1', '/media/demo.webm', 3, 'HIDDEN', '2026-11-12T05:51:25.593+00:00'),
    (21, 1, NULL, 'Final demo · Relational data in motion', '/media/demo.webm', 3, 'PUBLISHED', '2026-11-12T05:53:51.711+00:00'),
    (22, 1, NULL, 'Final demo · Relational data in motion', '/media/demo.webm', 3, 'PUBLISHED', '2026-11-12T05:57:37.68+00:00'),
    (23, 1, NULL, 'Final demo · Relational data in motion 1794463240774', '/media/demo.webm', 3, 'PUBLISHED', '2026-11-12T06:00:50.316+00:00');

INSERT INTO douyin."COMMENT" (comment_id, video_id, author_id, parent_comment_id, body_text, comment_status, created_at) VALUES
    (1, 1, 2, NULL, 'Nice campus walk', 'VISIBLE', '2026-11-06T09:00:00+00:00'),
    (2, 1, 1, 1, 'Thank you', 'VISIBLE', '2026-11-06T09:01:00+00:00'),
    (3, 1, 3, 2, 'Where is this?', 'VISIBLE', '2026-11-06T09:02:00+00:00'),
    (4, 1, 4, 1, 'A hidden reply', 'HIDDEN', '2026-11-06T09:03:00+00:00'),
    (5, 1, 5, 4, 'A visible reply to a hidden anchor', 'VISIBLE', '2026-11-06T09:04:00+00:00'),
    (6, 2, 1, NULL, 'Which cafe?', 'VISIBLE', '2026-11-06T10:00:00+00:00'),
    (7, 3, 2, NULL, 'Useful SQL example', 'VISIBLE', '2026-11-06T11:00:00+00:00'),
    (8, 4, 1, NULL, 'Retained after video hiding', 'VISIBLE', '2026-11-06T12:00:00+00:00'),
    (9, 3, 1, 7, 'More examples next time', 'VISIBLE', '2026-11-06T11:01:00+00:00'),
    (15, 11, 1, NULL, 'Committed before hiding', 'VISIBLE', '2026-11-12T05:49:46.343+00:00'),
    (22, 17, 1, NULL, 'Committed before hiding', 'VISIBLE', '2026-11-12T05:51:21.408+00:00'),
    (23, 21, 1, NULL, 'This comment was posted through the verified prototype.', 'VISIBLE', '2026-11-12T05:53:56.362+00:00'),
    (24, 22, 1, NULL, 'This comment was posted through the verified prototype.', 'VISIBLE', '2026-11-12T05:57:41.874+00:00'),
    (25, 23, 1, NULL, 'This comment was posted through the verified prototype.', 'VISIBLE', '2026-11-12T06:00:55.01+00:00');

INSERT INTO douyin."VIDEO_TOPIC" (video_id, topic_id, tagged_at) VALUES
    (1, 1, '2026-11-02T09:00:01+00:00'),
    (1, 2, '2026-11-02T09:00:02+00:00'),
    (2, 2, '2026-11-02T10:00:01+00:00'),
    (3, 1, '2026-11-03T09:00:01+00:00'),
    (3, 3, '2026-11-03T09:00:02+00:00'),
    (4, 4, '2026-11-03T10:00:01+00:00'),
    (5, 1, '2026-11-04T09:00:01+00:00'),
    (6, 2, '2026-11-04T10:00:01+00:00'),
    (6, 4, '2026-11-04T10:00:02+00:00');

INSERT INTO douyin."VIDEO_LIKE" (user_id, video_id, liked_at) VALUES
    (1, 1, '2026-11-06T13:00:00+00:00'),
    (1, 2, '2026-11-06T13:03:00+00:00'),
    (1, 4, '2026-11-06T13:08:00+00:00'),
    (1, 8, '2026-11-06T13:11:00+00:00'),
    (1, 21, '2026-11-12T05:53:59.289+00:00'),
    (1, 22, '2026-11-12T05:57:44.779+00:00'),
    (1, 23, '2026-11-12T06:00:57.941+00:00'),
    (2, 1, '2026-11-06T13:01:00+00:00'),
    (2, 3, '2026-11-06T13:05:00+00:00'),
    (2, 4, '2026-11-06T13:09:00+00:00'),
    (3, 1, '2026-11-06T13:02:00+00:00'),
    (4, 2, '2026-11-06T13:04:00+00:00'),
    (4, 3, '2026-11-06T13:06:00+00:00'),
    (5, 3, '2026-11-06T13:07:00+00:00'),
    (5, 6, '2026-11-06T13:10:00+00:00');

INSERT INTO douyin."FOLLOW" (follower_id, followed_id, followed_at) VALUES
    (1, 2, '2026-11-06T14:00:00+00:00'),
    (1, 3, '2026-11-06T14:02:00+00:00'),
    (2, 1, '2026-11-06T14:01:00+00:00'),
    (2, 3, '2026-11-06T14:04:00+00:00'),
    (3, 1, '2026-11-06T14:03:00+00:00'),
    (4, 1, '2026-11-06T14:05:00+00:00'),
    (5, 1, '2026-11-06T14:06:00+00:00'),
    (5, 2, '2026-11-06T14:07:00+00:00');

INSERT INTO douyin."COLLECTION" (collection_id, owner_id, collection_name, created_at) VALUES
    (1, 1, 'Study', '2026-11-06T15:00:00+00:00'),
    (2, 1, 'Favorites', '2026-11-06T15:01:00+00:00'),
    (3, 2, 'Study', '2026-11-06T15:02:00+00:00'),
    (4, 5, 'Empty', '2026-11-06T15:03:00+00:00'),
    (5, 1, 'Concurrency verification 1794462584687498000', '2026-11-12T05:49:44.241+00:00'),
    (6, 1, 'Concurrency verification 1794462591504306000', '2026-11-12T05:49:51.071+00:00'),
    (8, 1, 'Concurrency verification 1794462680123695000', '2026-11-12T05:51:19.753+00:00'),
    (9, 1, 'Concurrency verification 1794462685929304000', '2026-11-12T05:51:25.593+00:00'),
    (10, 1, 'Final demo 1794462842945', '2026-11-12T05:54:03.967+00:00'),
    (11, 1, 'Final demo 1794463067983', '2026-11-12T05:57:48.995+00:00'),
    (12, 1, 'Final demo 1794463240774', '2026-11-12T06:01:02.65+00:00');

INSERT INTO douyin."COLLECTION_ITEM" (collection_id, item_no, video_id, added_at) VALUES
    (1, 1, 1, '2026-11-06T16:00:00+00:00'),
    (1, 2, 3, '2026-11-06T16:01:00+00:00'),
    (2, 1, 1, '2026-11-06T16:02:00+00:00'),
    (2, 2, 4, '2026-11-06T16:03:00+00:00'),
    (3, 1, 2, '2026-11-06T16:04:00+00:00'),
    (9, 1, 20, '2026-11-12T05:51:27.194+00:00'),
    (9, 2, 19, '2026-11-12T05:51:27.195+00:00'),
    (10, 1, 21, '2026-11-12T05:54:08.161+00:00'),
    (10, 2, 22, '2026-11-12T05:57:50.309+00:00'),
    (12, 1, 23, '2026-11-12T06:01:06.827+00:00');

SELECT setval(pg_get_serial_sequence('douyin."USER"', 'user_id'), 6, true);

SELECT setval(pg_get_serial_sequence('douyin."MUSIC"', 'music_id'), 3, true);

SELECT setval(pg_get_serial_sequence('douyin."TOPIC"', 'topic_id'), 5, true);

SELECT setval(pg_get_serial_sequence('douyin."VIDEO"', 'video_id'), 23, true);

SELECT setval(pg_get_serial_sequence('douyin."COMMENT"', 'comment_id'), 25, true);

SELECT setval(pg_get_serial_sequence('douyin."COLLECTION"', 'collection_id'), 12, true);

COMMIT;
