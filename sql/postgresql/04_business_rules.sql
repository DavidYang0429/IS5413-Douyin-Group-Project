-- PostgreSQL 17. Private, database-authenticated course application interface.
-- No table/column changes: 10 entities and 43 fields remain unchanged.
CREATE FUNCTION douyin.actor_id() RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE actor bigint;
BEGIN
    IF session_user !~ '^douyin_demo_u[1-5]$' THEN
        RAISE EXCEPTION 'A dedicated demo database login is required' USING ERRCODE='42501';
    END IF;
    actor := substring(session_user from '([1-5])$')::bigint;
    IF NOT EXISTS (SELECT 1 FROM douyin."USER" WHERE user_id=actor AND account_status='ACTIVE') THEN
        RAISE EXCEPTION 'Account is unavailable' USING ERRCODE='42501';
    END IF;
    RETURN actor;
END $$;

CREATE FUNCTION douyin.guard_interaction() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE state text; parent_video bigint;
BEGIN
    IF TG_TABLE_NAME='COMMENT' AND TG_OP='UPDATE' THEN
        IF NEW.comment_id IS DISTINCT FROM OLD.comment_id
           OR NEW.video_id IS DISTINCT FROM OLD.video_id
           OR NEW.author_id IS DISTINCT FROM OLD.author_id
           OR NEW.parent_comment_id IS DISTINCT FROM OLD.parent_comment_id THEN
            RAISE EXCEPTION 'Comment identity, author, video and parent are immutable' USING ERRCODE='23514';
        END IF;
        RETURN NEW;
    END IF;
    SELECT visibility_status INTO state FROM douyin."VIDEO" WHERE video_id=NEW.video_id FOR SHARE;
    IF NOT FOUND THEN RAISE EXCEPTION 'Video does not exist' USING ERRCODE='23503'; END IF;
    IF state <> 'PUBLISHED' THEN RAISE EXCEPTION 'Hidden videos cannot receive new interactions' USING ERRCODE='23514'; END IF;
    IF TG_TABLE_NAME='COMMENT' THEN
      IF NEW.parent_comment_id IS NOT NULL THEN
        IF NEW.parent_comment_id=NEW.comment_id THEN
            RAISE EXCEPTION 'A comment cannot reply to itself' USING ERRCODE='23514';
        END IF;
        SELECT video_id INTO parent_video FROM douyin."COMMENT" WHERE comment_id=NEW.parent_comment_id FOR KEY SHARE;
        IF NOT FOUND THEN RAISE EXCEPTION 'Parent comment does not exist' USING ERRCODE='23503'; END IF;
        IF parent_video <> NEW.video_id THEN
            RAISE EXCEPTION 'Parent and reply must reference the same video' USING ERRCODE='23514';
        END IF;
        -- Existing parent only + immutable ancestry prevents insertion of cycles.
      END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_comment BEFORE INSERT OR UPDATE ON douyin."COMMENT"
    FOR EACH ROW EXECUTE FUNCTION douyin.guard_interaction();
CREATE TRIGGER guard_like BEFORE INSERT OR UPDATE ON douyin."VIDEO_LIKE"
    FOR EACH ROW EXECUTE FUNCTION douyin.guard_interaction();
CREATE TRIGGER guard_collection_item BEFORE INSERT OR UPDATE ON douyin."COLLECTION_ITEM"
    FOR EACH ROW EXECUTE FUNCTION douyin.guard_interaction();

CREATE FUNCTION douyin.guard_ownership() RETURNS trigger
LANGUAGE plpgsql SET search_path = pg_catalog AS $$
BEGIN
    IF TG_TABLE_NAME='VIDEO' THEN
        IF NEW.creator_id IS DISTINCT FROM OLD.creator_id OR NEW.video_id IS DISTINCT FROM OLD.video_id THEN
            RAISE EXCEPTION 'Video identity and creator are immutable' USING ERRCODE='23514';
        END IF;
    ELSE
        IF NEW.owner_id IS DISTINCT FROM OLD.owner_id OR NEW.collection_id IS DISTINCT FROM OLD.collection_id THEN
            RAISE EXCEPTION 'Collection identity and owner are immutable' USING ERRCODE='23514';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER guard_video_owner BEFORE UPDATE ON douyin."VIDEO"
    FOR EACH ROW EXECUTE FUNCTION douyin.guard_ownership();
CREATE TRIGGER guard_collection_owner BEFORE UPDATE ON douyin."COLLECTION"
    FOR EACH ROW EXECUTE FUNCTION douyin.guard_ownership();

CREATE FUNCTION douyin.app(action text, payload jsonb DEFAULT '{}'::jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog AS $$
DECLARE
    actor bigint := douyin.actor_id();
    vid bigint; cid bigint; obj bigint; n integer; result jsonb; owner bigint;
BEGIN
    IF payload ?| ARRAY['actor_id','user_id','creator_id','owner_id','author_id'] THEN
        RAISE EXCEPTION 'Identity is determined by the database login' USING ERRCODE='42501';
    END IF;
    IF action='profile' THEN
        SELECT jsonb_build_object('user_id',user_id,'nickname',nickname) INTO result
        FROM douyin."USER" WHERE user_id=actor;
        RETURN result;
    ELSIF action='bootstrap' THEN
        RETURN jsonb_build_object('profile',douyin.app('profile'),
          'users',(SELECT coalesce(jsonb_agg(jsonb_build_object('user_id',user_id,'nickname',nickname) ORDER BY user_id),'[]'::jsonb) FROM douyin."USER" WHERE account_status='ACTIVE'),
          'topics',(SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY topic_id),'[]'::jsonb) FROM douyin."TOPIC" t),
          'music',(SELECT coalesce(jsonb_agg(jsonb_build_object('music_id',music_id,'title',title) ORDER BY music_id),'[]'::jsonb) FROM douyin."MUSIC"));
    ELSIF action='feed' THEN
        SELECT coalesce(jsonb_agg(to_jsonb(v) ORDER BY v.video_id DESC),'[]'::jsonb) INTO result FROM (
            SELECT v.*,u.nickname,
              (SELECT count(*) FROM douyin."VIDEO_LIKE" l WHERE l.video_id=v.video_id) AS like_count,
              EXISTS(SELECT 1 FROM douyin."VIDEO_LIKE" l WHERE l.video_id=v.video_id AND l.user_id=actor) AS liked,
              EXISTS(SELECT 1 FROM douyin."FOLLOW" f WHERE f.follower_id=actor AND f.followed_id=v.creator_id) AS following,
              v.creator_id=actor AS is_mine
            FROM douyin."VIDEO" v JOIN douyin."USER" u ON u.user_id=v.creator_id
            WHERE (v.visibility_status='PUBLISHED' OR v.creator_id=actor)
              AND (coalesce(payload->>'search','')='' OR v.caption ILIKE '%'||(payload->>'search')||'%')
        ) v;
        RETURN result;
    ELSIF action='comments' THEN
        vid := (payload->>'video_id')::bigint;
        IF NOT EXISTS (SELECT 1 FROM douyin."VIDEO" WHERE video_id=vid AND (visibility_status='PUBLISHED' OR creator_id=actor)) THEN
            RAISE EXCEPTION 'Video is not available' USING ERRCODE='42501';
        END IF;
        WITH RECURSIVE thread AS (
          SELECT c.*,0 AS depth,ARRAY[c.comment_id] AS path FROM douyin."COMMENT" c
          WHERE c.video_id=vid AND parent_comment_id IS NULL
          UNION ALL
          SELECT c.*,p.depth+1,p.path||c.comment_id FROM thread p JOIN douyin."COMMENT" c ON c.parent_comment_id=p.comment_id
          WHERE c.video_id=vid AND NOT c.comment_id=ANY(p.path)
        ) SELECT coalesce(jsonb_agg(jsonb_build_object('comment_id',comment_id,'parent_comment_id',parent_comment_id,'depth',depth,
          'body_text',CASE WHEN comment_status='VISIBLE' THEN body_text ELSE '[hidden]' END,
          'author_id',CASE WHEN comment_status='VISIBLE' THEN author_id END,'status',comment_status) ORDER BY path),'[]'::jsonb)
          INTO result FROM thread;
        RETURN result;
    ELSIF action='collections' THEN
        SELECT coalesce(jsonb_agg(jsonb_build_object('collection_id',c.collection_id,'name',c.collection_name,
          'items',(SELECT coalesce(jsonb_agg(jsonb_build_object('item_no',i.item_no,'video_id',v.video_id,'caption',v.caption) ORDER BY i.item_no),'[]'::jsonb)
                   FROM douyin."COLLECTION_ITEM" i JOIN douyin."VIDEO" v ON v.video_id=i.video_id AND v.visibility_status='PUBLISHED' WHERE i.collection_id=c.collection_id)
          ) ORDER BY c.collection_id),'[]'::jsonb) INTO result FROM douyin."COLLECTION" c WHERE c.owner_id=actor;
        RETURN result;
    ELSIF action='publish' THEN
        INSERT INTO douyin."VIDEO" (creator_id,music_id,caption,media_url,duration_seconds)
          VALUES (actor,(payload->>'music_id')::bigint,coalesce(payload->>'caption',''),payload->>'media_url',(payload->>'duration_seconds')::numeric)
          RETURNING video_id INTO vid;
        RETURN jsonb_build_object('video_id',vid);
    ELSIF action IN ('hide','unhide','edit','tag','untag') THEN
        vid := (payload->>'video_id')::bigint;
        SELECT creator_id INTO owner FROM douyin."VIDEO" WHERE video_id=vid FOR UPDATE;
        IF owner IS DISTINCT FROM actor THEN RAISE EXCEPTION 'Only the creator may modify this video' USING ERRCODE='42501'; END IF;
        IF action IN ('hide','unhide') THEN
            UPDATE douyin."VIDEO" SET visibility_status=CASE WHEN action='hide' THEN 'HIDDEN' ELSE 'PUBLISHED' END WHERE video_id=vid;
        ELSIF action='edit' THEN
            UPDATE douyin."VIDEO" SET caption=coalesce(payload->>'caption','') WHERE video_id=vid;
        ELSIF action='tag' THEN
            INSERT INTO douyin."VIDEO_TOPIC" (video_id,topic_id) VALUES (vid,(payload->>'topic_id')::bigint) ON CONFLICT DO NOTHING;
        ELSE
            DELETE FROM douyin."VIDEO_TOPIC" WHERE video_id=vid AND topic_id=(payload->>'topic_id')::bigint;
        END IF;
        RETURN jsonb_build_object('video_id',vid,'action',action);
    ELSIF action IN ('like','unlike') THEN
        vid := (payload->>'video_id')::bigint;
        IF action='like' THEN
            INSERT INTO douyin."VIDEO_LIKE" (user_id,video_id) VALUES (actor,vid) ON CONFLICT DO NOTHING;
        ELSE
            DELETE FROM douyin."VIDEO_LIKE" WHERE user_id=actor AND video_id=vid;
        END IF;
        RETURN jsonb_build_object('video_id',vid,'liked',action='like');
    ELSIF action IN ('follow','unfollow') THEN
        obj := (payload->>'target_user_id')::bigint;
        IF action='follow' THEN
            INSERT INTO douyin."FOLLOW" (follower_id,followed_id) VALUES (actor,obj) ON CONFLICT DO NOTHING;
        ELSE
            DELETE FROM douyin."FOLLOW" WHERE follower_id=actor AND followed_id=obj;
        END IF;
        RETURN jsonb_build_object('target_user_id',obj,'following',action='follow');
    ELSIF action='comment' THEN
        INSERT INTO douyin."COMMENT" (video_id,author_id,parent_comment_id,body_text)
          VALUES ((payload->>'video_id')::bigint,actor,(payload->>'parent_comment_id')::bigint,payload->>'body_text')
          RETURNING comment_id INTO obj;
        RETURN jsonb_build_object('comment_id',obj);
    ELSIF action='create_collection' THEN
        INSERT INTO douyin."COLLECTION" (owner_id,collection_name) VALUES (actor,btrim(payload->>'name')) RETURNING collection_id INTO cid;
        RETURN jsonb_build_object('collection_id',cid);
    ELSIF action IN ('collect','remove_collection_item') THEN
        cid := (payload->>'collection_id')::bigint;
        SELECT owner_id INTO owner FROM douyin."COLLECTION" WHERE collection_id=cid FOR UPDATE;
        IF owner IS DISTINCT FROM actor THEN RAISE EXCEPTION 'Only the owner may modify this collection' USING ERRCODE='42501'; END IF;
        IF action='remove_collection_item' THEN
            DELETE FROM douyin."COLLECTION_ITEM" WHERE collection_id=cid AND item_no=(payload->>'item_no')::integer;
            RETURN jsonb_build_object('removed',true);
        END IF;
        vid := (payload->>'video_id')::bigint;
        SELECT item_no INTO n FROM douyin."COLLECTION_ITEM" WHERE collection_id=cid AND video_id=vid;
        IF FOUND THEN RETURN jsonb_build_object('item_no',n,'already_present',true); END IF;
        SELECT coalesce(max(item_no),0)+1 INTO n FROM douyin."COLLECTION_ITEM" WHERE collection_id=cid;
        INSERT INTO douyin."COLLECTION_ITEM" (collection_id,item_no,video_id) VALUES (cid,n,vid);
        RETURN jsonb_build_object('item_no',n,'already_present',false);
    END IF;
    RAISE EXCEPTION 'Unknown application action' USING ERRCODE='22023';
END $$;

-- No table grants. No browser/API callable privileged functions.
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA douyin FROM PUBLIC, anon, authenticated, service_role;
GRANT USAGE ON SCHEMA douyin TO douyin_demo_u1, douyin_demo_u2, douyin_demo_u3, douyin_demo_u4, douyin_demo_u5;
GRANT EXECUTE ON FUNCTION douyin.app(text,jsonb) TO douyin_demo_u1, douyin_demo_u2, douyin_demo_u3, douyin_demo_u4, douyin_demo_u5;
