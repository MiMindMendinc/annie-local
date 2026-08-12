-- Keep one durable active-session state row per user.
-- Existing duplicate rows are reduced to the highest epoch / latest restart.

DELETE FROM chat_sessions AS older
USING chat_sessions AS newer
WHERE older.user_id = newer.user_id
  AND (
    older.epoch < newer.epoch
    OR (older.epoch = newer.epoch AND older.restarted_at < newer.restarted_at)
    OR (
      older.epoch = newer.epoch
      AND older.restarted_at = newer.restarted_at
      AND older.id < newer.id
    )
  );

CREATE UNIQUE INDEX IF NOT EXISTS uq_chat_sessions_user
    ON chat_sessions (user_id);
