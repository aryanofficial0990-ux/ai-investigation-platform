import json
import requests

from llm.graph_service import query_graph


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"


def ask_llm(prompt: str, json_mode: bool = False) -> str:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    if json_mode:
        payload["format"] = "json"

    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=60
    )

    response.raise_for_status()

    result = response.json()
    return result.get("response", "").strip()


def parse_question(question: str) -> dict:
    prompt = f"""
You are an investigation query parser.

Convert the investigator's question into a JSON object.

Return ONLY valid JSON.
Do not use markdown.
Do not add explanations.

Allowed intents:
- find_relationship
- find_entity
- find_connections
- find_path
- find_transactions
- find_locations
- find_communications

Rules:
1. If the question asks how two specific entities are connected,
   use "find_relationship".
2. If the question asks for all entities connected to one entity,
   use "find_connections".
3. If the question asks for the shortest path between two entities,
   use "find_path".
4. If the question asks about financial transactions,
   use "find_transactions".
5. If the question asks about locations,
   use "find_locations".
6. If the question asks about calls or communication,
   use "find_communications".
7. Never invent entity names.
8. If an entity is not mentioned, return an empty string.

Question:
{question}

Return exactly:

{{
    "intent": "find_relationship",
    "source_entity": "Person A",
    "target_entity": "Account XYZ234"
}}
"""

    for attempt in range(2):
        try:
            raw_output = ask_llm(prompt, json_mode=True)

            parsed = json.loads(raw_output)

            required_keys = {
                "intent",
                "source_entity",
                "target_entity"
            }

            if not required_keys.issubset(parsed.keys()):
                raise ValueError("Missing required JSON fields")

            return parsed

        except (json.JSONDecodeError, ValueError):
            if attempt == 0:
                print("\nLLM returned invalid JSON. Retrying...")
            else:
                print("\nLLM could not produce valid JSON.")
                raise

    raise RuntimeError("Unable to parse investigator question.")


def generate_answer(question: str, graph_result: dict) -> str:
    prompt = f"""
You are an investigation assistance AI.

Answer the investigator's question using ONLY the graph information
provided below.

Do not invent facts.
Do not add information that is not present.
Mention the evidence supporting the relationship.

INVESTIGATOR QUESTION:
{question}

GRAPH RESULT:
{json.dumps(graph_result, indent=2)}

Give a concise, evidence-based answer.
"""

    return ask_llm(prompt)


def main():
    question = "How is Person A connected to Account XYZ234?"

    print("\nInvestigator Question:")
    print(question)

    # Step 1: Understand the question
    parsed_query = parse_question(question)

    print("\nStructured Query:")
    print(json.dumps(parsed_query, indent=2))

    # Step 2: Retrieve graph information
    graph_result = query_graph(
        intent=parsed_query["intent"],
        source_entity=parsed_query["source_entity"],
        target_entity=parsed_query["target_entity"]
    )

    print("\nGraph Result:")
    print(json.dumps(graph_result, indent=2))

    # Step 3: Generate grounded answer
    if graph_result.get("found"):
        answer = generate_answer(
            question,
            graph_result
        )

        print("\nInvestigation Answer:")
        print(answer)

    else:
        print("\nNo verified relationship found.")


if __name__ == "__main__":
    main()