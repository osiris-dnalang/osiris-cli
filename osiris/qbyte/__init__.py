"""osiris.qbyte — QByte mining system."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class QByteBlock:
    """A QByte mining block."""
    block_id: int
    nonce: int = 0
    lambda_coherence: float = 0.0
    phi_fidelity: float = 0.0
    hash: str = ""
    valid: bool = False


class QByteMiner:
    """QByte proof-of-coherence mining engine."""

    def __init__(self, difficulty: float = 0.7734):
        self.difficulty = difficulty
        self.chain: List[QByteBlock] = []

    def mine_block(self, lambda_c: float, phi: float) -> QByteBlock:
        import hashlib
        block = QByteBlock(
            block_id=len(self.chain),
            lambda_coherence=lambda_c,
            phi_fidelity=phi,
        )
        data = f"{block.block_id}:{lambda_c}:{phi}"
        block.hash = hashlib.sha256(data.encode()).hexdigest()[:16]
        block.valid = phi >= self.difficulty
        if block.valid:
            self.chain.append(block)
        return block

    def chain_length(self) -> int:
        return len(self.chain)
