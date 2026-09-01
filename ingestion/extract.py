import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from paddleocr import PaddleOCR
import google.generativeai as genai

# Load secret environment variables
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# 1. Suppress OCR debug logs
logging.getLogger("ppocr").setLevel(logging.ERROR)

# 2. Configure Gemini API
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-3.6-flash')

# 3. Initialize OCR Engine
print("Initializing PaddleOCR Engine...")
ocr = PaddleOCR(use_angle_cls=True, lang='en', enable_mkldnn=False)

# 4. Setup Input and Output Folders
input_dir = Path("inputs")
output_dir = Path("outputs")
input_dir.mkdir(exist_ok=True)
output_dir.mkdir(exist_ok=True)

print(f"Looking for FIR images in the '{input_dir.name}' folder...\n")
print("=" * 60)

valid_extensions = {".jpg", ".jpeg", ".png"}

# 5. Loop through every image in the inputs folder
for image_path in input_dir.iterdir():
    if image_path.suffix.lower() in valid_extensions:
        print(f"-> Processing {image_path.name}...")
        
        try:
            # Step A: Text Extraction
            raw_result = ocr.ocr(str(image_path))
            lines = []
            
            if isinstance(raw_result, list) and len(raw_result) > 0 and isinstance(raw_result[0], dict):
                texts = raw_result[0].get('rec_texts') or raw_result[0].get('rec_text') or []
                lines = [str(t).strip() for t in texts if str(t).strip()]
            elif isinstance(raw_result, list) and raw_result[0]:
                lines = [line[1][0].strip() for line in raw_result[0] if line[1][0].strip()]

            full_text = "\n".join(lines)
            
            # Step B: LLM-Based Zero-Shot Schema Mapping
            prompt = f"""
            Extract the following information from this Indian police complaint letter and return ONLY a valid JSON object. 
            If a field is missing, use null.
            
            Schema:
            {{
              "document_type": "FIRST INFORMATION REPORT / COMPLAINT",
              "fir_or_complaint_date": null,
              "police_station": null,
              "district_or_city": null,
              "complainant": {{
                "name": null,
                "relation_type": null,
                "relation_name": null,
                "address": null,
                "phone": null
              }},
              "incident_details": {{
                "date_of_incident": null,
                "description": null,
                "stolen_items": null,
                "stolen_amount_value": null,
                "ipc_sections_or_allegations": []
              }},
              "suspects_or_accused": [
                {{
                  "name": null,
                  "organization_or_address": null,
                  "phone_numbers": []
                }}
              ]
            }}

            Document Text:
            {full_text}
            """

            response = model.generate_content(prompt)
            
            # Clean markdown formatting
            json_string = response.text.strip()
            if json_string.startswith("```json"):
                json_string = json_string[7:]
            if json_string.endswith("```"):
                json_string = json_string[:-3]
                
            parsed_json = json.loads(json_string.strip())

            # Step C: Save structured output to the outputs folder
            output_file = output_dir / f"{image_path.name}_structured.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(parsed_json, f, indent=2, ensure_ascii=False)

            print(f"   [SUCCESS] Saved as {output_file.name}")

        except Exception as e:
            print(f"   [ERROR] Failed to process {image_path.name}: {e}")

print("\n" + "=" * 60)
print("BATCH INGESTION COMPLETE")