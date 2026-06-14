import sqlite3
import os

class MemoryIndexer:
    def __init__(self, db_path="~/.lmms/memory.db"):
        self.db_path = os.path.expanduser(db_path)
        
    def summarize_chat(self, session_id: str):
        if not os.path.exists(self.db_path):
            return
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if conversation needs summarizing
        cursor.execute("SELECT id, role, content FROM conversations WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
        messages = cursor.fetchall()
        
        if len(messages) < 10: # Only summarize if >10 messages
            conn.close()
            return
            
        # Get raw messages to summarize (all but last 4)
        to_summarize = messages[:-4]
        
        # In a real implementation, we'd call the LLM here to generate the summary
        # For now, we simulate this process.
        summary_text = f"Summary of {len(to_summarize)} earlier messages: User requested things, AI assisted."
        
        # We replace the old messages with a single system summary message
        # Delete old
        ids_to_delete = [m['id'] for m in to_summarize]
        cursor.executemany("DELETE FROM conversations WHERE id = ?", [(idx,) for idx in ids_to_delete])
        
        # Insert summary as the first message
        cursor.execute("INSERT INTO conversations (session_id, role, content, model_used, timestamp) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                       (session_id, "system", f"Context summary: {summary_text}", "system"))
                       
        conn.commit()
        conn.close()

if __name__ == "__main__":
    indexer = MemoryIndexer()
    # Replace 'test' with actual session_id if needed
    indexer.summarize_chat('test')
