import datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List
from hashing.hash_utils import canonical_serialize, hash_fir_json
from merkle.merkle_tree import MerkleTree

LEDGER_FILE = Path("chain_state.json")

class Block:
    def __init__(self, index: int, timestamp: str, action: str, records: List[Dict[str, Any]], merkle_root: str, prev_hash: str):
        self.index = index
        self.timestamp = timestamp
        self.action = action  # "INITIAL_INGESTION", "OFFICER_VERIFIED", "FIELD_EDIT"
        self.records = records
        self.merkle_root = merkle_root
        self.prev_hash = prev_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        header = {
            "index": self.index,
            "timestamp": self.timestamp,
            "action": self.action,
            "merkle_root": self.merkle_root,
            "prev_hash": self.prev_hash
        }
        return hashlib.sha256(canonical_serialize(header)).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "action": self.action,
            "merkle_root": self.merkle_root,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
            "records": self.records
        }

class StandaloneLedger:
    def __init__(self):
        self.chain: List[Block] = []
        self._load_or_genesis()

    def _load_or_genesis(self):
        if LEDGER_FILE.exists():
            with open(LEDGER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for b in data:
                    block = Block(b["index"], b["timestamp"], b["action"], b["records"], b["merkle_root"], b["prev_hash"])
                    block.hash = b["hash"]
                    self.chain.append(block)
        else:
            genesis = Block(0, "2026-01-01T00:00:00Z", "GENESIS", [], "0" * 64, "0" * 64)
            self.chain.append(genesis)
            self._persist()

    def _persist(self):
        with open(LEDGER_FILE, "w", encoding="utf-8") as f:
            json.dump([b.to_dict() for b in self.chain], f, indent=2)

    def append_batch(self, action: str, fir_records: List[Dict[str, Any]]) -> Block:
        leaf_hashes = [r["data_hash"] for r in fir_records]
        tree = MerkleTree(leaf_hashes)
        
        prev_block = self.chain[-1]
        new_block = Block(
            index=len(self.chain),
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            action=action,
            records=fir_records,
            merkle_root=tree.root,
            prev_hash=prev_block.hash
        )
        self.chain.append(new_block)
        self._persist()
        return new_block

    def verify_integrity(self) -> bool:
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i - 1]
            if curr.prev_hash != prev.hash or curr.calculate_hash() != curr.hash:
                print(f"[ALERT] Tampering detected at Block #{curr.index}")
                return False
        print("[AUDIT PASSED] Chain integrity 100% verified.")
        return True

if __name__ == "__main__":
    outputs_path = Path("../ingestion/outputs")
    json_files = list(outputs_path.glob("*.json"))
    
    if not json_files:
        print("No JSON files found in ../ingestion/outputs")
        exit()

    print(f"Locking {len(json_files)} extracted FIRs into Genesis State...")
    records = [hash_fir_json(f) for f in json_files]

    ledger = StandaloneLedger()
    block = ledger.append_batch("INITIAL_AI_INGESTION", records)
    print(f"Successfully anchored to Block #{block.index}")
    print(f"Merkle Root: {block.merkle_root}")
    ledger.verify_integrity()