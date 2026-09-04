"""
Graph service layer.

The LLM talks to this file instead of directly talking to
the graph database.

Currently:
    graph_service -> FastAPI backend -> mock graph

Later:
    graph_service -> FastAPI backend -> Neo4j Aura
"""

import requests


BACKEND_URL = "http://127.0.0.1:8000"


def query_graph(
    intent: str,
    source_entity: str = None,
    target_entity: str = None,
):
    """
    Query the backend graph API.

    The backend currently returns mock graph data.
    Later it will return data from Neo4j Aura.
    """

    response = requests.get(
        f"{BACKEND_URL}/graph-data",
        timeout=10
    )

    response.raise_for_status()

    graph_data = response.json()

    return graph_data