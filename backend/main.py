import os
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Allow frontend to connect without CORS errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to Docker Neo4j
URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "dummy_password123")

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

@app.get("/graph-data")
async def get_live_graph():
    # The Cypher query to get nodes (n, m) and relationships (r)
    query = "MATCH (n)-[r]->(m) RETURN n, r, m"
    
    nodes_dict = {}
    edges_list = []
    
    with driver.session() as session:
        result = session.run(query)
        
        for record in result:
            # Extract source node
            node_n = record["n"]
            n_id = node_n.element_id
            if n_id not in nodes_dict:
                nodes_dict[n_id] = {"data": {"id": n_id, "label": dict(node_n).get("name", "Unknown"), **dict(node_n)}}
            
            # Extract target node
            node_m = record["m"]
            m_id = node_m.element_id
            if m_id not in nodes_dict:
                nodes_dict[m_id] = {"data": {"id": m_id, "label": dict(node_m).get("name", "Unknown"), **dict(node_m)}}
            
            # Extract relationship
            rel_r = record["r"]
            edges_list.append({
                "data": {
                    "id": rel_r.element_id,
                    "source": rel_r.start_node.element_id,
                    "target": rel_r.end_node.element_id,
                    "label": rel_r.type,
                    **dict(rel_r)
                }
            })

    return {
        "status": "success",
        "data": {
            "elements": {
                "nodes": list(nodes_dict.values()),
                "edges": edges_list
            }
        }
    }


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Endpoint for uploading FIR documents or images.
    Member 3's PaddleOCR and spaCy scripts will eventually plug in here.
    """
    
    # 1. Read the uploaded file into memory
    file_content = await file.read()
    
    # 2. PLACEHOLDER FOR MEMBER 3's AI PIPELINE
    # This is where Member 3 will take 'file_content' and run their NLP extraction.
    # extracted_data = run_ai_pipeline(file_content)
    
    # Mocking what Member 3's AI might return for now:
    mock_extracted_entities = [
        {"entity_type": "Person", "name": "Walter White", "role": "Suspect"},
        {"entity_type": "Location", "name": "Albuquerque Warehouse", "type": "Industrial"}
    ]
    
    # 3. PLACEHOLDER FOR DATABASE INSERTION
    # Later, you will write a Cypher query here to push these new entities into Neo4j.
    
    return {
        "status": "success",
        "message": f"Successfully received '{file.filename}'.",
        "size_bytes": len(file_content),
        "ai_extraction_preview": mock_extracted_entities
    }