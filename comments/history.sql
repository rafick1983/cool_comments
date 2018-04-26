CREATE OR REPLACE FUNCTION comment_history()
  RETURNS trigger AS
$BODY$
begin
  INSERT INTO comments_history(comment_id, event_date, user_id, old_comment, new_comment, old_is_removed, new_is_removed)
  VALUES (NEW.id, now(), NEW.changed_by_id, OLD.comment, NEW.comment, OLD.is_removed, NEW.is_removed);
  return NEW;
end;$BODY$
  LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS comment_history on {table_name};

CREATE TRIGGER comment_history
  AFTER UPDATE
  ON {table_name}
  FOR EACH ROW
  EXECUTE PROCEDURE comment_history();
