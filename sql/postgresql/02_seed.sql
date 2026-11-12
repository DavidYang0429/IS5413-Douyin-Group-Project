-- Synthetic course fixtures, not real Douyin users or accessible media.
-- Apply once, only after 01_schema.sql and only when all ten tables are empty.
-- All event timestamps are fixed UTC values. No destructive reset is included.
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
            RAISE EXCEPTION 'Seed refused: douyin.% already contains data', t;
        END IF;
    END LOOP;
END;
$seed_guard$;

INSERT INTO douyin."USER" (user_id, phone, nickname, account_status, registered_at) VALUES
    (1, '+19990000001', 'Demo_Ada',   'ACTIVE',   '2026-11-01 08:00:00+00'),
    (2, '+19990000002', 'Demo_Ben',   'ACTIVE',   '2026-11-01 08:01:00+00'),
    (3, '+19990000003', 'Demo_Chen',  'ACTIVE',   '2026-11-01 08:02:00+00'),
    (4, '+19990000004', 'Demo_Dina',  'ACTIVE',   '2026-11-01 08:03:00+00'),
    (5, '+19990000005', 'Demo_Eli',   'ACTIVE',   '2026-11-01 08:04:00+00'),
    (6, '+19990000006', 'Demo_Faye',  'DISABLED', '2026-11-01 08:05:00+00');

INSERT INTO douyin."MUSIC" (music_id, title, artist_name, audio_url) VALUES
    (1, 'Campus Beat', 'Demo Artist A', 'https://example.invalid/audio/campus.mp3'),
    (2, 'Coffee Loop', 'Demo Artist B', 'https://example.invalid/audio/coffee.mp3'),
    (3, 'Practice Track', 'Demo Artist C', 'https://example.invalid/audio/practice.mp3');

INSERT INTO douyin."TOPIC" (topic_id, topic_name) VALUES
    (1, 'Study'), (2, 'Life'), (3, 'SQL'), (4, 'Music'), (5, 'Unused');

INSERT INTO douyin."VIDEO"
    (video_id, creator_id, music_id, caption, media_url, duration_seconds, visibility_status, published_at) VALUES
    (1, 1, 1, 'CityU campus walk', 'https://example.invalid/video/1.mp4', 25.500, 'PUBLISHED', '2026-11-02 09:00:00+00'),
    (2, 2, 2, 'Coffee in Hong Kong', 'https://example.invalid/video/2.mp4', 18.000, 'PUBLISHED', '2026-11-02 10:00:00+00'),
    (3, 1, NULL, 'SQL joins explained', 'https://example.invalid/video/3.mp4', 55.125, 'PUBLISHED', '2026-11-03 09:00:00+00'),
    (4, 3, 3, 'Hidden rehearsal', 'https://example.invalid/video/4.mp4', 30.000, 'PUBLISHED', '2026-11-03 10:00:00+00'),
    (5, 3, NULL, 'Study desk setup', 'https://example.invalid/video/5.mp4', 12.500, 'PUBLISHED', '2026-11-04 09:00:00+00'),
    (6, 4, 1, 'Harbour sunset', 'https://example.invalid/video/6.mp4', 40.000, 'PUBLISHED', '2026-11-04 10:00:00+00'),
    (7, 2, NULL, 'An empty interaction example', 'https://example.invalid/video/7.mp4', 10.000, 'PUBLISHED', '2026-11-05 09:00:00+00'),
    (8, 4, NULL, '', 'https://example.invalid/video/8.mp4', 5.250, 'PUBLISHED', '2026-11-05 10:00:00+00');

INSERT INTO douyin."VIDEO_TOPIC" (video_id, topic_id, tagged_at) VALUES
    (1, 1, '2026-11-02 09:00:01+00'), (1, 2, '2026-11-02 09:00:02+00'),
    (2, 2, '2026-11-02 10:00:01+00'), (3, 1, '2026-11-03 09:00:01+00'),
    (3, 3, '2026-11-03 09:00:02+00'), (4, 4, '2026-11-03 10:00:01+00'),
    (5, 1, '2026-11-04 09:00:01+00'), (6, 2, '2026-11-04 10:00:01+00'),
    (6, 4, '2026-11-04 10:00:02+00');

INSERT INTO douyin."COMMENT"
    (comment_id, video_id, author_id, parent_comment_id, body_text, comment_status, created_at) VALUES
    (1, 1, 2, NULL, 'Nice campus walk', 'VISIBLE', '2026-11-06 09:00:00+00'),
    (2, 1, 1, 1, 'Thank you', 'VISIBLE', '2026-11-06 09:01:00+00'),
    (3, 1, 3, 2, 'Where is this?', 'VISIBLE', '2026-11-06 09:02:00+00'),
    (4, 1, 4, 1, 'A hidden reply', 'HIDDEN', '2026-11-06 09:03:00+00'),
    (5, 1, 5, 4, 'A visible reply to a hidden anchor', 'VISIBLE', '2026-11-06 09:04:00+00'),
    (6, 2, 1, NULL, 'Which cafe?', 'VISIBLE', '2026-11-06 10:00:00+00'),
    (7, 3, 2, NULL, 'Useful SQL example', 'VISIBLE', '2026-11-06 11:00:00+00'),
    (8, 4, 1, NULL, 'Retained after video hiding', 'VISIBLE', '2026-11-06 12:00:00+00'),
    (9, 3, 1, 7, 'More examples next time', 'VISIBLE', '2026-11-06 11:01:00+00');

INSERT INTO douyin."VIDEO_LIKE" (user_id, video_id, liked_at) VALUES
    (1, 1, '2026-11-06 13:00:00+00'), (2, 1, '2026-11-06 13:01:00+00'),
    (3, 1, '2026-11-06 13:02:00+00'), (1, 2, '2026-11-06 13:03:00+00'),
    (4, 2, '2026-11-06 13:04:00+00'), (2, 3, '2026-11-06 13:05:00+00'),
    (4, 3, '2026-11-06 13:06:00+00'), (5, 3, '2026-11-06 13:07:00+00'),
    (1, 4, '2026-11-06 13:08:00+00'), (2, 4, '2026-11-06 13:09:00+00'),
    (5, 6, '2026-11-06 13:10:00+00'), (1, 8, '2026-11-06 13:11:00+00');

INSERT INTO douyin."FOLLOW" (follower_id, followed_id, followed_at) VALUES
    (1, 2, '2026-11-06 14:00:00+00'), (2, 1, '2026-11-06 14:01:00+00'),
    (1, 3, '2026-11-06 14:02:00+00'), (3, 1, '2026-11-06 14:03:00+00'),
    (2, 3, '2026-11-06 14:04:00+00'), (4, 1, '2026-11-06 14:05:00+00'),
    (5, 1, '2026-11-06 14:06:00+00'), (5, 2, '2026-11-06 14:07:00+00');

INSERT INTO douyin."COLLECTION" (collection_id, owner_id, collection_name, created_at) VALUES
    (1, 1, 'Study', '2026-11-06 15:00:00+00'),
    (2, 1, 'Favorites', '2026-11-06 15:01:00+00'),
    (3, 2, 'Study', '2026-11-06 15:02:00+00'),
    (4, 5, 'Empty', '2026-11-06 15:03:00+00');

INSERT INTO douyin."COLLECTION_ITEM" (collection_id, item_no, video_id, added_at) VALUES
    (1, 1, 1, '2026-11-06 16:00:00+00'), (1, 2, 3, '2026-11-06 16:01:00+00'),
    (2, 1, 1, '2026-11-06 16:02:00+00'), (2, 2, 4, '2026-11-06 16:03:00+00'),
    (3, 1, 2, '2026-11-06 16:04:00+00');

-- Hide after creating interactions; detail rows are retained.
UPDATE douyin."VIDEO" SET visibility_status = 'HIDDEN' WHERE video_id = 4;

-- Keep identity sequences ahead of explicit fixture identifiers.
SELECT setval(pg_get_serial_sequence('douyin."USER"', 'user_id'), 6, true);
SELECT setval(pg_get_serial_sequence('douyin."MUSIC"', 'music_id'), 3, true);
SELECT setval(pg_get_serial_sequence('douyin."TOPIC"', 'topic_id'), 5, true);
SELECT setval(pg_get_serial_sequence('douyin."VIDEO"', 'video_id'), 8, true);
SELECT setval(pg_get_serial_sequence('douyin."COMMENT"', 'comment_id'), 9, true);
SELECT setval(pg_get_serial_sequence('douyin."COLLECTION"', 'collection_id'), 4, true);
COMMIT;
