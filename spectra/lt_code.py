"""Luby Transform fountain code: robust-soliton degree distribution,
seed-derived (untransmitted) neighbor selection, belief-propagation peeling
decoder. This is the FEC referenced in the SPECTRA spec (Sec. 6.1, 9)."""
import math
import random


def robust_soliton(K: int, c: float = 0.03, delta: float = 0.5):
    ideal = [0.0] * (K + 1)
    ideal[1] = 1.0 / K
    for i in range(2, K + 1):
        ideal[i] = 1.0 / (i * (i - 1))

    S = c * math.log(K / delta) * math.sqrt(K)
    spike = max(1, min(K, int(K / max(S, 1e-9))))
    tau = [0.0] * (K + 1)
    for i in range(1, spike):
        tau[i] = S / (K * i)
    tau[spike] = S * math.log(S / delta) / K

    mu = [ideal[i] + tau[i] for i in range(K + 1)]
    Z = sum(mu)
    return [m / Z for m in mu]


def _cdf(K: int):
    mu = robust_soliton(K)
    out, cum = [], 0.0
    for p in mu:
        cum += p
        out.append(cum)
    return out


def _sample_degree(cdf, rng: random.Random) -> int:
    r = rng.random()
    for d, c in enumerate(cdf):
        if r <= c:
            return d
    return len(cdf) - 1


def _xor_bytes(dst: bytearray, src: bytes) -> None:
    for i in range(len(dst)):
        dst[i] ^= src[i]


class LTEncoder:
    """Encodes symbols from `blocks` (list[bytes], equal length). Neighbor
    indices are derived deterministically from (seed, packet_id) so they
    never need to be transmitted -- only DEGREE travels in the header."""

    def __init__(self, blocks: list, seed: int):
        self.blocks = blocks
        self.K = len(blocks)
        self.block_size = len(blocks[0]) if blocks else 0
        self.seed = seed & 0xFFFFFFFF
        self.cdf = _cdf(self.K) if self.K else [1.0]

    def _rng(self, packet_id: int) -> random.Random:
        s = (self.seed * 1000003) ^ (packet_id * 2654435761) ^ self.K
        return random.Random(s & 0xFFFFFFFF)

    def indices_for(self, packet_id: int):
        rng = self._rng(packet_id)
        d = max(1, min(_sample_degree(self.cdf, rng), self.K))
        return rng.sample(range(self.K), d)

    def encode_symbol(self, packet_id: int):
        idx = self.indices_for(packet_id)
        data = bytearray(self.block_size)
        for i in idx:
            _xor_bytes(data, self.blocks[i])
        return len(idx), bytes(data)


class LTDecoder:
    """Belief-propagation peeling decoder. Recomputes the same neighbor
    indices the encoder used, given the packet_id carried in each header."""

    def __init__(self, K: int, block_size: int, seed: int):
        self.K = K
        self.block_size = block_size
        self.seed = seed & 0xFFFFFFFF
        self.cdf = _cdf(K) if K else [1.0]
        self.resolved = {}
        self.pending = []  # list[[set(indices), bytearray]]

    def _rng(self, packet_id: int) -> random.Random:
        s = (self.seed * 1000003) ^ (packet_id * 2654435761) ^ self.K
        return random.Random(s & 0xFFFFFFFF)

    def indices_for(self, packet_id: int):
        rng = self._rng(packet_id)
        d = max(1, min(_sample_degree(self.cdf, rng), self.K))
        return set(rng.sample(range(self.K), d))

    def add_symbol(self, packet_id: int, data: bytes) -> None:
        idx = self.indices_for(packet_id)
        self.pending.append([idx, bytearray(data)])
        self._peel()

    def _peel(self) -> None:
        changed = True
        while changed:
            changed = False
            for entry in self.pending:
                idx, data = entry
                for i in list(idx):
                    if i in self.resolved:
                        _xor_bytes(data, self.resolved[i])
                        idx.discard(i)
                        changed = True
                if len(idx) == 1:
                    (only,) = tuple(idx)
                    if only not in self.resolved:
                        self.resolved[only] = bytes(data)
                        changed = True
            self.pending = [e for e in self.pending if len(e[0]) > 0]

    def is_complete(self) -> bool:
        return len(self.resolved) == self.K

    def get_blocks(self) -> list:
        return [self.resolved[i] for i in range(self.K)]
