import os
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db  # shared Neo4jConnection instance -- single source of truth

load_dotenv()

#<<<<<<< feature/backend-init
# --- App Initialization ---------------------------------------------------
app = FastAPI(title="CodeTitans Investigation API")

# --- CORS -----------------------------------------------------------------

app = FastAPI(title="CodeTitans Investigation API")

# --- CORS -----------------------------------------------------------------
# NOTE: allow_origins=["*"] + allow_credentials=True is invalid per the CORS
# spec -- browsers reject it. List real origins instead.
#>>>>>>> main
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

#<<<<<<< feature/backend-init
# --- Mock Data Fallback ---------------------------------------------------
# Used when Neo4j is offline, or when db.connected is False for any reason.
MOCK_GRAPH = {
    "nodes": [
        {"data": {"id": "v", "label": "Vikram Singh\n(Mastermind)", "name": "Vikram Singh", "role": "Mastermind", "node_type": "Person"}},
        {"data": {"id": "p", "label": "Priya Sharma\n(Financier)", "name": "Priya Sharma", "role": "Financier", "node_type": "Person"}},
        {"data": {"id": "r", "label": "Rahul Verma\n(Logistics)", "name": "Rahul Verma", "role": "Logistics", "node_type": "Person"}},
        {"data": {"id": "w", "label": "Okhla Warehouse\n(Location)", "name": "Okhla Warehouse", "node_type": "Location"}},
        {"data": {"id": "c", "label": "MH01XX1234\n(Vehicle)", "plate": "MH01XX1234", "node_type": "Vehicle"}}
    ],
    "edges": [
        {
            "data": {
                "id": "e1",
                "source": "v",
                "target": "p",
                "label": "COMMUNICATED_WITH",
                "source_evidence": "FIR_001",
                "confidence": 0.88,
                "timestamp": "2026-03-01T10:00:00Z",
                "status": "AI_SUGGESTED",
                "state": "AI_SUGGESTED"
            }
        },
        {
            "data": {
                "id": "e2",
                "source": "p",
                "target": "r",
                "label": "TRANSFERRED_FUNDS",
                "source_evidence": "BANK_003",
                "confidence": 1.0,
                "timestamp": "2026-03-02T14:30:00Z",
                "status": "CONFIRMED",
                "state": "CONFIRMED"
            }
        }
    ]
}


# --- Request Models ---------------------------------------------------
class EdgeDecision(BaseModel):
    edge_id: str
    status: str | None = None
    new_state: str | None = None


# --- Base Endpoints -------------------------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "service": "CodeTitans Investigation API"}
#=======
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

#>>>>>>> main


@app.get("/health")
def health():
    return {"neo4j_connected": db.connected, "mode": "live" if db.connected else "mock"}


# --- Graph Retrieval Endpoint ---------------------------------------------
@app.get("/graph-data")
#<<<<<<< feature/backend-init
async def get_graph_data():
    """
    Returns {nodes, edges} formatted for Cytoscape.js.
    Falls back to MOCK_GRAPH if Neo4j is offline.
    """
    if not db.connected or db.driver is None:
        return MOCK_GRAPH

    query = "MATCH (n)-[r]->(m) RETURN n, r, m"
    nodes_dict = {}
    edges_list = []

    try:
        with db.driver.session() as session:
            result = session.run(query)
#=======
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
#>>>>>>> main

            for record in result:
                # Process nodes
                for node in (record["n"], record["m"]):
                    n_id = str(node.element_id)
                    if n_id not in nodes_dict:
                        props = dict(node)
                        # Derive a readable display label
                        display_name = props.get("name") or props.get("plate") or (list(node.labels)[0] if node.labels else "Unknown")
                        role_tag = f"\n({props.get('role')})" if props.get("role") else ""

                        nodes_dict[n_id] = {
                            "data": {
                                **props,
                                "id": n_id,
                                "label": f"{display_name}{role_tag}",
                                "node_type": list(node.labels)[0] if node.labels else "Entity"
                            }
                        }

                # Process edge
                rel_r = record["r"]
                props = dict(rel_r)

                # Support both 'state' and 'status' to prevent frontend style breaks
                edge_status = props.get("status") or props.get("state") or "AI_SUGGESTED"
                edge_conf = props.get("confidence") if props.get("confidence") is not None else props.get("link_conf", 0.0)

                edges_list.append({
                    "data": {
                        "id": str(rel_r.element_id),
                        "source": str(rel_r.start_node.element_id),
                        "target": str(rel_r.end_node.element_id),
                        "label": rel_r.type,
                        "source_evidence": props.get("source") or props.get("source_id") or "unknown",
                        "confidence": edge_conf,
                        "timestamp": props.get("timestamp"),
                        "status": edge_status,
                        "state": edge_status
                    }
                })

        return {"nodes": list(nodes_dict.values()), "edges": edges_list}

    except Exception as e:
        print(f"[graph-data] Query failed: {e}. Falling back to mock graph.")
        return MOCK_GRAPH


# --- Human-in-the-Loop Decision Endpoint ----------------------------------
@app.post("/api/edge/decision")
async def update_edge_decision(payload: EdgeDecision):
    """
    Updates the verification state of an edge (CONFIRMED / REJECTED).
    Fulfills human-in-the-loop and contestable AI requirements.
    """
    new_status = payload.status or payload.new_state or "CONFIRMED"

    if not db.connected or db.driver is None:
        return {"status": "mock_success", "edge_id": payload.edge_id, "new_status": new_status}

    query = """
    MATCH ()-[r]->()
    WHERE elementId(r) = $edge_id
    SET r.status = $new_status,
        r.state = $new_status,
        r.confidence = CASE WHEN $new_status = 'CONFIRMED' THEN 1.0 ELSE 0.0 END
    RETURN elementId(r) AS id, r.status AS status
    """
    try:
        with db.driver.session() as session:
            result = session.run(query, edge_id=payload.edge_id, new_status=new_status)
            record = result.single()

        if record is None:
            return {"status": "error", "detail": f"No edge found with id {payload.edge_id}"}

        return {"status": "success", "edge_id": payload.edge_id, "new_status": new_status}

    except Exception as e:
        print(f"[edge-decision] Query failed: {e}")
        return {"status": "error", "detail": str(e)}


# --- Document Upload Placeholder -----------------------------------------
@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Endpoint for uploading FIR documents or reports for OCR + NER ingestion.
    """
    file_content = await file.read()

    mock_extracted_entities = [
        {"entity_type": "Person", "name": "Vikram Singh", "role": "Suspect"},
        {"entity_type": "Location", "name": "Okhla Warehouse", "type": "Industrial"}
    ]

    return {
        "status": "success",
        "filename": file.filename,
        "size_bytes": len(file_content),
        "ai_extraction_preview": mock_extracted_entities,
#<<<<<<< feature/backend-init
    }
#=======
    }
#>>>>>>> main
