import os
import time
import json
import logging
import requests
from pathlib import Path
import numpy as np
from PIL import Image

# 1. Fix Windows crashes and disable incompatible mkldnn
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"
logging.getLogger("ppocr").setLevel(logging.ERROR)

from paddleocr import PaddleOCR

# 2. Initialize PaddleOCR securely offline
ocr = PaddleOCR(lang='en', enable_mkldnn=False, use_textline_orientation=False)

input_dir = Path("inputs")
output_dir = Path("outputs")
output_dir.mkdir(exist_ok=True)

MAX_SIDE = 1280

def load_and_resize(img_path, max_side=MAX_SIDE):
    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    scale = max_side / max(w, h)
    if scale < 1:
        img = img.resize((int(w * scale), int(h * scale)))
    return np.array(img)

def safe_extract_text(result):
    """Robustly handles multiple PaddleOCR/PaddleX output structures."""
    texts = []
    if not result: return texts
    
    for page in result:
        if page is None: continue
        
        if hasattr(page, 'rec_texts') and page.rec_texts:
            texts.extend([str(t) for t in page.rec_texts])
            continue
            
        if hasattr(page, 'get') and page.get('rec_texts'):
            texts.extend([str(t) for t in page.get('rec_texts')])
            continue

        if isinstance(page, (list, tuple)):
            for line in page:
                try:
                    text_part = line[1]
                    if isinstance(text_part, (tuple, list)) and len(text_part) > 0:
                        texts.append(str(text_part[0]))
                    elif isinstance(text_part, str):
                        texts.append(text_part)
                except (IndexError, TypeError, KeyError):
                    continue
    return texts
def parse_with_ollama(raw_text):
    prompt = f"""
    You are an AI forensics assistant. Read the OCR text from this First Information Report (FIR) 
    and return ONLY valid JSON matching this exact structure. 
    Separate specific identifiers like license plates, addresses, bank accounts, and officer names for graph linking.
    
    {{
        "fir_no": "string",
        "district": "string",
        "police_station": "string",
        "date_reported": "string",
        "date_occurrence": "string",
        "crime_type": "string",
        "acts_sections": ["list of legal sections"],
        "investigating_officer": "string",
        "complainant": {{
            "name": "string",
            "address": "string"
        }},
        "accused": [
            {{
                "name": "string",
                "address": "string"
            }}
        ],
        "stolen_properties": {{
            "vehicles": [
                {{
                    "make_model": "string",
                    "color": "string",
                    "license_plate": "string"
                }}
            ],
            "cash_value": "string or null",
            "other_items": ["list of items like laptops, jewelry, etc."]
        }},
        "digital_and_financial_indicators": {{
            "bank_accounts": ["list of account numbers"],
            "upi_ids": ["list of UPI IDs"],
            "phone_numbers": ["list of phone numbers"]
        }},
        "incident_location": "string",
        "narrative": "A brief 2-sentence summary of the incident"
    }}

    Document Text:
    {raw_text}
    """
    
    try:
        response = requests.post("http://localhost:11434/api/generate", json={
            "model": "llama3.1",
            "prompt": prompt,
            "format": "json",
            "stream": False
        }, timeout=120)
        response.raise_for_status()
        return json.loads(response.json()['response'])
    
    except requests.exceptions.ConnectionError:
        print("[FATAL] Ollama is not running. Please start Ollama in the background.")
        return None
    except Exception as e:
        print(f"[ERROR] Local LLM parsing failed: {e}")
        return None

def process_pipeline():
    images = sorted(list(input_dir.glob("*.jpg")))
    
    for img_path in images:
        output_file = output_dir / f"{img_path.stem}_structured.json"
        
        # Delete the existing JSON to force reprocessing
        if output_file.exists():
            output_file.unlink()
            
        print(f"-> Processing {img_path.name}...")

        try:
            start_time = time.time()  # Start tracking time

            # 1. OCR Extraction (Offline Vision)
            img_array = load_and_resize(img_path)
            result = ocr.predict(img_array) 
            
            raw_text_blocks = safe_extract_text(result)
            full_text = "\n".join(raw_text_blocks)

            if not full_text.strip():
                print(f"[WARNING] No text found for {img_path.name}")
                continue

            # 2. LLM Structuring (Offline NLP)
            structured_data = parse_with_ollama(full_text)

            if structured_data:
                with open(output_file, 'w') as f:
                    json.dump(structured_data, f, indent=4)
                
                end_time = time.time()  # Stop tracking time
                elapsed = end_time - start_time
                
                print(f"[SUCCESS] Exported -> {output_file.name} (Took {elapsed:.2f} seconds)")

        except Exception as e:
            print(f"[ERROR] {img_path.name}: {e}")

if __name__ == "__main__":
    process_pipeline()
    print("Air-gapped ingestion complete.")