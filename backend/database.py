import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


class Neo4jConnection:
    """Thin wrapper around the official Neo4j driver.

    Connection failures are caught here, not raised -- so the API can
    still start and be tested even with zero database running. Once
    Member 1's Neo4j instance is up and .env points at it, this
    reconnects automatically the next time the server restarts.
    """

    def __init__(self, uri: str, user: str, password: str):
        self.uri = uri
        self.driver = None
        self.connected = False
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            self.connected = True
            print(f"[Neo4j] Connected to {uri}")
        except Exception as e:
            print(f"[Neo4j] Could not connect ({e}). Running in MOCK MODE.")
            self.connected = False

    def close(self):
        if self.driver:
            self.driver.close()

    def query(self, cypher: str, parameters: dict | None = None) -> list[dict]:
        if not self.connected or not self.driver:
            raise RuntimeError("Neo4j is not connected")
        with self.driver.session() as session:
            result = session.run(cypher, parameters or {})
            return [record.data() for record in result]


# One shared connection for the whole app (imported by main.py).
# Built once, at import time -- if Neo4j isn't running, `db.connected`
# will just be False and the API falls back to mock data.
db = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
