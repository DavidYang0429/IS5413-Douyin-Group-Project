-- A fixed whitelist of the ten submitted SELECT queries; not arbitrary SQL.
CREATE FUNCTION douyin.report(report_id text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog AS $$
DECLARE actor bigint := douyin.actor_id(); result jsonb;
BEGIN
IF actor <> 1 THEN RAISE EXCEPTION 'Reports require the demonstration operator account' USING ERRCODE='42501'; END IF;
IF report_id='Q01' THEN
SELECT coalesce(jsonb_agg(to_jsonb(q)), '[]'::jsonb) INTO result FROM (
SELECT v.video_id, v.caption, v.duration_seconds, v.published_at,
       u.nickname AS creator, m.title AS music_title
FROM douyin."VIDEO" v
JOIN douyin."USER" u ON u.user_id = v.creator_id
LEFT JOIN douyin."MUSIC" m ON m.music_id = v.music_id
WHERE v.creator_id = 1 AND v.visibility_status = 'PUBLISHED'
ORDER BY v.published_at DESC, v.video_id DESC
) q;
ELSIF report_id='Q02' THEN
SELECT coalesce(jsonb_agg(to_jsonb(q)), '[]'::jsonb) INTO result FROM (
SELECT t.topic_name, v.video_id, v.caption, u.nickname AS creator
FROM douyin."TOPIC" t
JOIN douyin."VIDEO_TOPIC" vt ON vt.topic_id = t.topic_id
JOIN douyin."VIDEO" v ON v.video_id = vt.video_id
JOIN douyin."USER" u ON u.user_id = v.creator_id
WHERE t.topic_name = 'Study' AND v.visibility_status = 'PUBLISHED'
ORDER BY v.video_id
) q;
ELSIF report_id='Q03' THEN
SELECT coalesce(jsonb_agg(to_jsonb(q)), '[]'::jsonb) INTO result FROM (
SELECT v.video_id, v.caption, COUNT(l.user_id) AS like_count
FROM douyin."VIDEO" v
LEFT JOIN douyin."VIDEO_LIKE" l ON l.video_id = v.video_id
WHERE v.visibility_status = 'PUBLISHED'
GROUP BY v.video_id, v.caption
ORDER BY v.video_id
) q;
ELSIF report_id='Q04' THEN
SELECT coalesce(jsonb_agg(to_jsonb(q)), '[]'::jsonb) INTO result FROM (
-- Hidden text and author identity are never emitted. A cycle guard bounds traversal.
WITH RECURSIVE thread AS (
    SELECT c.comment_id, c.parent_comment_id, c.author_id, c.body_text,
           c.comment_status, c.created_at, 0 AS depth, ARRAY[c.comment_id] AS path
    FROM douyin."COMMENT" c
    JOIN douyin."VIDEO" v ON v.video_id = c.video_id
    WHERE c.video_id = 1 AND c.parent_comment_id IS NULL
      AND v.visibility_status = 'PUBLISHED'
    UNION ALL
    SELECT c.comment_id, c.parent_comment_id, c.author_id, c.body_text,
           c.comment_status, c.created_at, p.depth + 1, p.path || c.comment_id
    FROM thread p
    JOIN douyin."COMMENT" c ON c.parent_comment_id = p.comment_id AND c.video_id = 1
    WHERE NOT c.comment_id = ANY(p.path)
)
SELECT comment_id, parent_comment_id, depth,
       CASE WHEN comment_status = 'VISIBLE' THEN author_id END AS author_id,
       CASE WHEN comment_status = 'VISIBLE' THEN body_text ELSE '[hidden]' END AS display_text,
       comment_status, created_at
FROM thread ORDER BY path
) q;
ELSIF report_id='Q05' THEN
SELECT coalesce(jsonb_agg(to_jsonb(q)), '[]'::jsonb) INTO result FROM (
SELECT 'following' AS direction, u.user_id, u.nickname, f.followed_at
FROM douyin."FOLLOW" f
JOIN douyin."USER" u ON u.user_id = f.followed_id
WHERE f.follower_id = 1
UNION ALL
SELECT 'follower' AS direction, u.user_id, u.nickname, f.followed_at
FROM douyin."FOLLOW" f
JOIN douyin."USER" u ON u.user_id = f.follower_id
WHERE f.followed_id = 1
ORDER BY direction, user_id
) q;
ELSIF report_id='Q06' THEN
SELECT coalesce(jsonb_agg(to_jsonb(q)), '[]'::jsonb) INTO result FROM (
SELECT u.user_id, u.nickname
FROM douyin."FOLLOW" outgoing
JOIN douyin."FOLLOW" incoming
  ON incoming.follower_id = outgoing.followed_id
 AND incoming.followed_id = outgoing.follower_id
JOIN douyin."USER" u ON u.user_id = outgoing.followed_id
WHERE outgoing.follower_id = 1
ORDER BY u.user_id
) q;
ELSIF report_id='Q07' THEN
SELECT coalesce(jsonb_agg(to_jsonb(q)), '[]'::jsonb) INTO result FROM (
-- Put visibility inside the join subquery so a hidden-only collection is not lost.
SELECT c.collection_id, c.collection_name, visible.item_no, visible.video_id,
       visible.caption, visible.added_at
FROM douyin."COLLECTION" c
LEFT JOIN (
    SELECT ci.collection_id, ci.item_no, ci.video_id, v.caption, ci.added_at
    FROM douyin."COLLECTION_ITEM" ci
    JOIN douyin."VIDEO" v ON v.video_id = ci.video_id AND v.visibility_status = 'PUBLISHED'
) visible ON visible.collection_id = c.collection_id
WHERE c.owner_id = 1
ORDER BY c.collection_id, visible.item_no
) q;
ELSIF report_id='Q08' THEN
SELECT coalesce(jsonb_agg(to_jsonb(q)), '[]'::jsonb) INTO result FROM (
WITH counts AS (
    SELECT v.video_id, v.caption, COUNT(l.user_id) AS like_count
    FROM douyin."VIDEO" v
    LEFT JOIN douyin."VIDEO_LIKE" l ON l.video_id = v.video_id
    WHERE v.visibility_status = 'PUBLISHED'
    GROUP BY v.video_id, v.caption
)
SELECT video_id, caption, like_count,
       DENSE_RANK() OVER (ORDER BY like_count DESC) AS popularity_rank
FROM counts ORDER BY like_count DESC, video_id LIMIT 10
) q;
ELSIF report_id='Q09' THEN
SELECT coalesce(jsonb_agg(to_jsonb(q)), '[]'::jsonb) INTO result FROM (
SELECT u.user_id, u.nickname, COUNT(v.video_id) AS published_video_count
FROM douyin."USER" u
LEFT JOIN douyin."VIDEO" v
  ON v.creator_id = u.user_id AND v.visibility_status = 'PUBLISHED'
WHERE u.account_status = 'ACTIVE'
GROUP BY u.user_id, u.nickname
ORDER BY published_video_count DESC, u.user_id
) q;
ELSIF report_id='Q10' THEN
SELECT coalesce(jsonb_agg(to_jsonb(q)), '[]'::jsonb) INTO result FROM (
SELECT t.topic_id, t.topic_name, COUNT(DISTINCT v.video_id) AS published_video_count
FROM douyin."TOPIC" t
LEFT JOIN douyin."VIDEO_TOPIC" vt ON vt.topic_id = t.topic_id
LEFT JOIN douyin."VIDEO" v
  ON v.video_id = vt.video_id AND v.visibility_status = 'PUBLISHED'
GROUP BY t.topic_id, t.topic_name
ORDER BY published_video_count DESC, t.topic_id
) q;
ELSE RAISE EXCEPTION 'Unknown report' USING ERRCODE='22023';
END IF;
RETURN result;
END $$;
REVOKE ALL ON FUNCTION douyin.report(text) FROM PUBLIC, anon, authenticated, service_role;
GRANT EXECUTE ON FUNCTION douyin.report(text) TO douyin_demo_u1;
