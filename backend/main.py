import os
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="CodeTitans Investigation API")

# --- CORS -----------------------------------------------------------------
# NOTE: allow_origins=["*"] + allow_credentials=True is invalid per the CORS
# spec -- browsers reject it. List real origins instead.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Create React App default
        "http://localhost:5173",   # Vite default
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Neo4j connection -------------------------------------------------------
# NOTE: matches .env.example exactly -- NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD.
# If you rename these, update .env.example too or teammates silently fall
# back to defaults.
URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
USERNAME = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "dummy_password123")

driver = None
db_connected = False
try:
    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    driver.verify_connectivity()
    db_connected = True
    print(f"[Neo4j] Connected to {URI}")
except Exception as e:
    print(f"[Neo4j] Could not connect ({e}). Running in MOCK MODE.")
    db_connected = False

# --- Mock data --------------------------------------------------------------
# Used ONLY when Neo4j isn't reachable. Matches the flat {nodes, edges}
# shape documented in API_CONTRACT.md.
MOCK_GRAPH = {
    "nodes": [
        {"data": {"id": "p1", "label": "Person", "name": "Ravi Kumar"}},
        {"data": {"id": "l1", "label": "Location", "name": "Mumbai Central"}},
    ],
    "edges": [
        {
            "data": {
                "id": "e1", "source": "p1", "target": "l1", "label": "SEEN_AT",
                "source_evidence": "CCTV", "confidence": 0.65,
                "timestamp": "2026-01-14T11:05:00", "status": "unconfirmed",
            }
        }
    ],
}


@app.get("/")
def root():
    return {"status": "ok", "service": "CodeTitans backend"}


@app.get("/health")
def health():
    return {"neo4j_connected": db_connected, "mode": "live" if db_connected else "mock"}


@app.get("/graph-data")
async def get_live_graph():
    """
    Returns {nodes, edges} shaped for Cytoscape.js. Falls back to
    MOCK_GRAPH if Neo4j isn't reachable.
    """
    if not db_connected:
        return MOCK_GRAPH

    query = "MATCH (n)-[r]->(m) RETURN n, r, m"

    nodes_dict = {}
    edges_list = []

    with driver.session() as session:
        result = session.run(query)

        for record in result:
            for node in (record["n"], record["m"]):
                n_id = node.element_id
                if n_id not in nodes_dict:
                    props = dict(node)
                    # Spread properties FIRST, then force id/label last so a
                    # node property can never silently overwrite them.
                    nodes_dict[n_id] = {
                        "data": {
                            **props,
                            "id": n_id,
                            "label": props.get("name", "Unknown"),
                        }
                    }

            rel_r = record["r"]
            props = dict(rel_r)
            edges_list.append({
                "data": {
                    "id": rel_r.element_id,
                    "source": rel_r.start_node.element_id,
                    "target": rel_r.end_node.element_id,
                    "label": rel_r.type,
                    # Explicit pulls -- NOT a blind **props spread -- so a
                    # relationship's own "source" property (e.g. "CDR")
                    # can never overwrite the edge's source NODE id above.
                    "source_evidence": props.get("source"),
                    "confidence": props.get("confidence"),
                    "timestamp": props.get("timestamp"),
                    "status": props.get("status"),
                }
            })

    return {"nodes": list(nodes_dict.values()), "edges": edges_list}


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Endpoint for uploading FIR documents or images.
    Member 3's PaddleOCR and spaCy scripts will eventually plug in here.
    """
    file_content = await file.read()

    # PLACEHOLDER FOR MEMBER 3's AI PIPELINE
    # extracted_data = run_ai_pipeline(file_content)

    mock_extracted_entities = [
        {"entity_type": "Person", "name": "Walter White", "role": "Suspect"},
        {"entity_type": "Location", "name": "Albuquerque Warehouse", "type": "Industrial"},
    ]

    # PLACEHOLDER FOR DATABASE INSERTION
    # Later: Cypher query to push these new entities into Neo4j.

    return {
        "status": "success",
        "message": f"Successfully received '{file.filename}'.",
        "size_bytes": len(file_content),
        "ai_extraction_preview": mock_extracted_entities,
    }
