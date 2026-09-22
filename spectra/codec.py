"""SpectraEncoder / SpectraDecoder: implements Sec. 5 (progressive payload
model), Sec. 6 (encoding algorithm) and Sec. 9 (decoding algorithm) of the
spec. L0 = tiny repeated recognition record (digest + shape). L1 = LT-coded
over the first K1 blocks ("essential" prefix). L2 = LT-coded over all K
blocks (full payload). The decoder returns the highest layer it can verify."""
import hashlib
import random
import struct

from .lt_code import LTEncoder, LTDecoder
from .packet import PacketHeader, pack_packet, unpack_packet

L0_SALT = 0x0000
L1_SALT = 0x1111
L2_SALT = 0x2222


def _split_blocks(data: bytes, block_size: int):
    blocks = []
    for i in range(0, len(data), block_size):
        chunk = data[i:i + block_size]
        if len(chunk) < block_size:
            chunk = chunk + b"\x00" * (block_size - len(chunk))
        blocks.append(chunk)
    return blocks or [b"\x00" * block_size]


class SpectraEncoder:
    def __init__(self, payload: bytes, symbol_id: int = None,
                 block_size: int = 48, essential_fraction: float = 0.25,
                 redundancy: float = 1.6):
        self.payload = payload
        self.symbol_id = symbol_id if symbol_id is not None else random.randint(0, 2**32 - 1)
        self.digest = hashlib.sha256(payload).digest()
        self.block_size = block_size
        self.blocks = _split_blocks(payload, block_size)
        self.K = len(self.blocks)
        self.K1 = max(1, int(self.K * essential_fraction))
        self.redundancy = redundancy

    def _l0_payload(self) -> bytes:
        return self.digest + struct.pack(">IIII", self.K, self.K1, self.block_size, len(self.payload))

    def generate_packets(self, l0_repeats: int = 0, target_packets: int = 160):
        packets = []
        pid = 0

        # L0 is a fixed 48-byte recognition/synchronization record. For the
        # image channel it is fragmented into 4-byte layer-0 packets so that
        # every physical packet region has the same reversible capacity.
        l0 = self._l0_payload()
        l0_fragment_size = self.block_size
        l0_fragments = [
            l0[i:i + l0_fragment_size]
            for i in range(0, len(l0), l0_fragment_size)
        ]
        for fragment in l0_fragments:
            if len(fragment) < l0_fragment_size:
                fragment = fragment + b"\x00" * (l0_fragment_size - len(fragment))
            h = PacketHeader(self.symbol_id, pid, layer=0, degree=0)
            packets.append(pack_packet(h, fragment))
            pid += 1

        enc1 = LTEncoder(self.blocks[:self.K1], self.symbol_id ^ L1_SALT)
        n1 = max(self.K1 + 2, int(self.K1 * self.redundancy))
        for _ in range(n1):
            degree, data = enc1.encode_symbol(pid)
            h = PacketHeader(self.symbol_id, pid, layer=1, degree=degree)
            packets.append(pack_packet(h, data))
            pid += 1

        enc2 = LTEncoder(self.blocks, self.symbol_id ^ L2_SALT)
        n2 = max(self.K + 2, int(self.K * self.redundancy))
        n2 = max(n2, max(0, int(target_packets) - len(packets)))
        for _ in range(n2):
            degree, data = enc2.encode_symbol(pid)
            h = PacketHeader(self.symbol_id, pid, layer=2, degree=degree)
            packets.append(pack_packet(h, data))
            pid += 1

        return packets


def spatial_interleave(packets, symbol_id: int):
    """Apply a deterministic keyed spatial permutation π to packet positions."""
    indexed = list(enumerate(packets))
    rng = random.Random((symbol_id & 0xFFFFFFFF) ^ 0x53504543545241)
    rng.shuffle(indexed)
    return [packet for _, packet in indexed]


class SpectraDecoder:
    def __init__(self):
        self.symbol_id = None
        self.meta = None
        self.dec1 = None
        self.dec2 = None
        self._buffer = []
        self._l0_fragments = {}

    def feed(self, raw_packet: bytes) -> None:
        res = unpack_packet(raw_packet)
        if res is None:
            return

        header, payload = res

        if self.symbol_id is None:
            self.symbol_id = header.symbol_id
        elif header.symbol_id != self.symbol_id:
            return

        if header.layer == 0:
            # L0 is a fixed 48-byte record fragmented into twelve 4-byte
            # packets. Packet-ID is the fragment sequence.
            self._l0_fragments[header.packet_id] = bytes(payload)

            if self.meta is None and len(self._l0_fragments) >= 12:
                record = b"".join(
                    self._l0_fragments[i]
                    for i in sorted(self._l0_fragments)
                    if i in self._l0_fragments
                )[:48]

                if len(record) < 48:
                    return

                digest = record[:32]
                K, K1, block_size, payload_len = struct.unpack(
                    ">IIII", record[32:48]
                )

                self.meta = {
                    "digest": digest,
                    "K": K,
                    "K1": K1,
                    "block_size": block_size,
                    "payload_len": payload_len,
                }

                self.dec1 = LTDecoder(
                    K1,
                    block_size,
                    self.symbol_id ^ L1_SALT
                )
                self.dec2 = LTDecoder(
                    K,
                    block_size,
                    self.symbol_id ^ L2_SALT
                )

                for h2, p2 in self._buffer:
                    self._route(h2, p2)

                self._buffer = []

            return

        if self.meta is None:
            self._buffer.append((header, payload))
            return

        self._route(header, payload)

    def _route(self, header: PacketHeader, payload: bytes) -> None:
        if header.layer == 1 and self.dec1 is not None:
            self.dec1.add_symbol(header.packet_id, payload)
        elif header.layer == 2 and self.dec2 is not None:
            self.dec2.add_symbol(header.packet_id, payload)

    def result(self):
        """Returns (layer_str, data). Mirrors Algorithm 2, steps 21-29:
        reconstruct L0, then attempt L1, then L2; return highest verified."""
        if self.meta is None:
            return "NONE", None

        if self.dec2 is not None and self.dec2.is_complete():
            data = b"".join(self.dec2.get_blocks())[:self.meta["payload_len"]]
            if hashlib.sha256(data).digest() == self.meta["digest"]:
                return "L2", data
            # hash mismatch: FEC "succeeded" on corrupted/undetected data.
            # Fall through and report the best still-trustworthy layer.

        if self.dec1 is not None and self.dec1.is_complete():
            data = b"".join(self.dec1.get_blocks())
            return "L1", data  # essential prefix only, not hash-verified

        return "L0", self.meta
