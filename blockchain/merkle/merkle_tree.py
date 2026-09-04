import hashlib
from typing import List

class MerkleTree:
    def __init__(self, leaf_hashes: List[str]):
        if not leaf_hashes:
            raise ValueError("Leaf hashes list cannot be empty.")
        self.leaves = sorted(leaf_hashes)
        self.tree: List[List[str]] = [self.leaves]
        self._build_tree()

    def _hash_pair(self, left: str, right: str) -> str:
        combined = (left + right).encode("utf-8")
        return hashlib.sha256(combined).hexdigest()

    def _build_tree(self):
        current_layer = self.leaves
        while len(current_layer) > 1:
            next_layer = []
            for i in range(0, len(current_layer), 2):
                left = current_layer[i]
                right = current_layer[i + 1] if i + 1 < len(current_layer) else left
                next_layer.append(self._hash_pair(left, right))
            self.tree.append(next_layer)
            current_layer = next_layer

    @property
    def root(self) -> str:
        return self.tree[-1][0]