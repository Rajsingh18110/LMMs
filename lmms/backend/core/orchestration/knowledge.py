import sqlite3
import os
import json
from typing import Dict, Any, List

class KnowledgeGraph:
    """
    Lightweight embedded SQLite implementation of the LMMs Knowledge Graph.
    Nodes: Workspace, Chat, Task, File, GitCommit
    Edges: MODIFIED, DEPENDS_ON, BELONGS_TO, REFERENCES
    """
    def __init__(self, workspace_dir: str):
        self.db_path = os.path.join(workspace_dir, ".lmms", "knowledge.sqlite")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Nodes Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    properties TEXT
                )
            """)
            
            # Edges Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    source_id TEXT,
                    target_id TEXT,
                    relation TEXT NOT NULL,
                    properties TEXT,
                    PRIMARY KEY (source_id, target_id, relation),
                    FOREIGN KEY (source_id) REFERENCES nodes(id),
                    FOREIGN KEY (target_id) REFERENCES nodes(id)
                )
            """)
            conn.commit()

    def add_node(self, node_id: str, node_type: str, properties: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO nodes (id, type, properties) VALUES (?, ?, ?)",
                (node_id, node_type, json.dumps(properties))
            )
            conn.commit()

    def add_edge(self, source_id: str, target_id: str, relation: str, properties: Dict[str, Any] = None):
        if properties is None:
            properties = {}
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO edges (source_id, target_id, relation, properties) VALUES (?, ?, ?, ?)",
                (source_id, target_id, relation, json.dumps(properties))
            )
            conn.commit()

    def query_related(self, node_id: str, relation: str) -> List[Dict[str, Any]]:
        """Finds all nodes connected to node_id by the specified relation."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT n.id, n.type, n.properties 
                FROM edges e
                JOIN nodes n ON e.target_id = n.id
                WHERE e.source_id = ? AND e.relation = ?
            """, (node_id, relation))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "type": row[1],
                    "properties": json.loads(row[2])
                })
            return results
