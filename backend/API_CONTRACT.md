## API Contract

Base URL (local dev): `http://127.0.0.1:8000`

All endpoints are read/write JSON over HTTP. CORS is enabled for
`localhost:3000` (CRA) and `localhost:5173` (Vite) — if your dev server
runs on a different port, ask Member 2 to add it in `main.py`.

Interactive docs (click-to-test every endpoint): `http://127.0.0.1:8000/docs`

---

### `GET /`
Basic health check — confirms the server is up.

**Response**
```json
{ "status": "ok", "service": "CodeTitans backend" }
```

---

### `GET /health`
Tells you whether the API is serving real data from Neo4j or mock data
(useful while the database team is still setting up).

**Response**
```json
{ "neo4j_connected": false, "mode": "mock" }
```
`mode` will read `"live"` once Neo4j is connected — no other field names change.

---

### `GET /graph-data`
Returns the full investigation graph, pre-shaped for Cytoscape.js.
Falls back to a small mock graph if Neo4j isn't reachable yet, so this
endpoint is safe to build against right now.

**Response**
```json
{
  "nodes": [
    { "data": { "id": "p1", "label": "Person", "name": "Ravi Kumar" } },
    { "data": { "id": "l1", "label": "Location", "name": "Mumbai Central" } }
  ],
  "edges": [
    {
      "data": {
        "id": "e1",
        "source": "p1",
        "target": "l1",
        "type": "SEEN_AT",
        "source_evidence": "CCTV",
        "confidence": 0.65,
        "timestamp": "2026-01-14T11:05:00",
        "status": "unconfirmed"
      }
    }
  ]
}
```
Every edge always carries `source_evidence`, `confidence`, `timestamp`
and `status` — this is a Round 2 requirement, not optional metadata.

---

### `POST /ask`  — *(planned, not yet built)*
For the GraphRAG + LLM team. Takes a natural-language investigator
question, retrieves relevant graph context, and returns a grounded,
cited answer.

**Request**
```json
{ "question": "How is Ravi Kumar connected to Case #101?" }
```

**Response (proposed shape — confirm with backend before building against it)**
```json
{
  "answer": "Ravi Kumar called Anjali Singh, who is a suspect in Case #101.",
  "sources": [
    { "type": "relationship", "id": "e1", "evidence": "CDR" },
    { "type": "relationship", "id": "e3", "evidence": "FIR" }
  ],
  "confidence": 0.78,
  "timestamp": "2026-01-14T12:00:00"
}
```

---

### Status codes
| Code | Meaning |
|---|---|
| 200 | Success |
| 500 | Neo4j query failed (only possible in `"live"` mode) |

### Notes for the frontend/LLM team
- You never need Neo4j credentials or a local `.env` — just clone,
  `pip install -r requirements.txt`, `uvicorn main:app --reload`.
- Requires **Python 3.10+** (the backend code uses modern type hints).
- If `/health` shows `"mode": "mock"`, that's expected until the
  database team's Neo4j instance is live — the JSON shape won't change
  when it switches to `"live"`, so it's safe to build against now.
