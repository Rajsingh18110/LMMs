import sqlite3
import os

DB_PATH = os.path.expanduser("~/.lmms/tools/tool_registry.db")
FTS_DB_PATH = os.path.expanduser("~/.lmms/tools/tool_fts.db")

# Stop words to exclude from FTS queries.
# Includes both common English stop words AND query meta-verbs that carry no
# domain signal (e.g. the word 'search' in 'binary search algorithm' should
# not match tools named *_search).
STOP_WORDS = {
    # Common English
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "have", "has", "had", "will", "would", "could",
    "should", "may", "might", "shall", "can", "of", "in", "on", "at",
    "to", "for", "and", "or", "but", "not", "what", "how", "my", "me",
    "i", "you", "it", "we", "they", "this", "that", "with", "from",
    # Query meta-verbs — intent words that span all domains
    "search", "find", "get", "show", "list", "tell", "describe", "give",
    "make", "use", "using", "explain", "current", "popular", "best",
    "top", "latest", "some", "any", "please", "help", "me", "about",
    "algorithm", "want", "need", "know", "look",
}

def build_fts_index():
    """Build FTS5 virtual table from the main tools registry.
    Uses porter tokenizer for stemming (search -> search, searching -> search).
    """
    if not os.path.exists(DB_PATH):
        return False

    conn = sqlite3.connect(FTS_DB_PATH)
    conn.execute("DROP TABLE IF EXISTS tools_fts")
    conn.execute("""
        CREATE VIRTUAL TABLE tools_fts USING fts5(
            tool_id UNINDEXED,
            name,
            description,
            category,
            endpoint UNINDEXED,
            incomplete UNINDEXED,
            tokenize = 'porter unicode61'
        )
    """)

    # Pull all complete tools from the registry
    src = sqlite3.connect(DB_PATH)
    src.row_factory = sqlite3.Row
    rows = src.execute(
        "SELECT id, name, description, category, endpoint, incomplete FROM tools WHERE incomplete = 0"
    ).fetchall()
    src.close()

    conn.executemany(
        "INSERT INTO tools_fts (tool_id, name, description, category, endpoint, incomplete) VALUES (?, ?, ?, ?, ?, ?)",
        [(r["id"], r["name"] or "", r["description"] or "", r["category"] or "", r["endpoint"] or "", r["incomplete"]) for r in rows]
    )
    conn.commit()
    conn.close()
    return True


class ToolClassifier:
    def __init__(self):
        self.db_path = DB_PATH
        self.fts_db_path = FTS_DB_PATH
        self._ensure_fts_ready()

    def _ensure_fts_ready(self):
        """Build FTS index if missing or stale."""
        if not os.path.exists(self.fts_db_path):
            build_fts_index()

    def search(self, query: str, limit: int = 5):
        if not os.path.exists(self.fts_db_path):
            return []

        # Strip stop words and build FTS MATCH query
        tokens = [w for w in query.lower().split() if w.isalpha() and w not in STOP_WORDS]
        if not tokens:
            tokens = [w for w in query.lower().split() if w.isalpha()]
        if not tokens:
            return []

        # FTS5 MATCH: each token is AND-joined by default, which is too strict
        # Use OR by wrapping each token. Also use prefix matching (token*) for partial words.
        fts_query = " OR ".join(f'"{tok}"' for tok in tokens)

        conn = sqlite3.connect(self.fts_db_path)
        conn.row_factory = sqlite3.Row

        try:
            # Curated tools get a rank boost via CASE on category
            rows = conn.execute(f"""
                SELECT tool_id, name, description, category, endpoint, incomplete,
                       rank,
                       CASE WHEN category = 'curated' THEN 1 ELSE 0 END AS is_curated
                FROM tools_fts
                WHERE tools_fts MATCH ?
                ORDER BY is_curated DESC, rank
                LIMIT ?
            """, (fts_query, limit)).fetchall()

            return [dict(r) for r in rows]

        except Exception as e:
            # Fallback: if FTS query syntax error, rebuild and return empty
            print(f"[ToolClassifier] FTS error ({e}), falling back to LIKE")
            conn.close()
            return self._like_fallback(query, limit)
        finally:
            try:
                conn.close()
            except:
                pass

    def _like_fallback(self, query: str, limit: int) -> list:
        """Original LIKE-based search as safety net."""
        if not os.path.exists(self.db_path):
            return []
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            q = f"%{query.lower()}%"
            rows = conn.execute(
                "SELECT * FROM tools WHERE (LOWER(name) LIKE ? OR LOWER(description) LIKE ?) AND incomplete = 0 "
                "ORDER BY CASE WHEN category = 'curated' THEN 1 ELSE 0 END DESC LIMIT ?",
                (q, q, limit)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def rebuild_index(self):
        """Force rebuild of the FTS index (call after adding new tools)."""
        if os.path.exists(self.fts_db_path):
            os.remove(self.fts_db_path)
        return build_fts_index()


if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "weather"

    classifier = ToolClassifier()
    results = classifier.search(query, limit=5)
    print(f"\nQuery: '{query}'  →  {len(results)} results")
    for r in results:
        print(f"  [{r['name']}] ({r.get('category','?')}) — {str(r.get('description',''))[:90]}")
