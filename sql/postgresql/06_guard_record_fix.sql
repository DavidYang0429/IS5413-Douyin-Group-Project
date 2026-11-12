-- Resolve table-specific record fields only inside their table branch.
CREATE OR REPLACE FUNCTION douyin.guard_interaction() RETURNS trigger
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
