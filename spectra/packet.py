"""SPECTRA packet header, per the paper's Table 1:
MAGIC(12) VERSION(4) SYMBOL-ID(32) PACKET-ID(16) LAYER(2) DEGREE(6)
FLAGS(6) PAYLOAD-LEN(12) PAYLOAD(var) CRC-32(32).

Simplification vs. the raw bitstream in the spec: the header is padded to
the next byte boundary after PAYLOAD-LEN so PAYLOAD can be handled as plain
bytes. Everything else follows the field widths exactly."""
from dataclasses import dataclass
import zlib

from .bitstream import BitReader, BitWriter

MAGIC = 0xA5C     # 12-bit family identifier (arbitrary reference value)
VERSION = 1       # 4-bit protocol version
MAX_PAYLOAD = (1 << 12) - 1
MAX_LAYER = 2
MAX_DEGREE = (1 << 6) - 1
MAX_FLAGS = (1 << 6) - 1


@dataclass
class PacketHeader:
    symbol_id: int
    packet_id: int
    layer: int     # 0=recognition, 1=essential, 2=full payload
    degree: int
    flags: int = 0


def pack_packet(header: PacketHeader, payload: bytes) -> bytes:
    if len(payload) > MAX_PAYLOAD:
        raise ValueError("payload exceeds 12-bit PAYLOAD-LEN field")
    if not (0 <= header.layer <= MAX_LAYER):
        raise ValueError("LAYER must be 0, 1, or 2")
    if not (0 <= header.degree <= MAX_DEGREE):
        raise ValueError("DEGREE exceeds 6-bit field")
    if not (0 <= header.flags <= MAX_FLAGS):
        raise ValueError("FLAGS exceeds 6-bit field")
    bw = BitWriter()
    bw.write(MAGIC, 12)
    bw.write(VERSION, 4)
    bw.write(header.symbol_id & 0xFFFFFFFF, 32)
    bw.write(header.packet_id & 0xFFFF, 16)
    bw.write(header.layer & 0x3, 2)
    bw.write(header.degree & 0x3F, 6)
    bw.write(header.flags & 0x3F, 6)
    bw.write(len(payload), 12)
    bw.align()
    body = bw.getvalue() + payload
    crc = zlib.crc32(body) & 0xFFFFFFFF
    return body + crc.to_bytes(4, "big")


def unpack_packet(data: bytes):
    """Returns (PacketHeader, payload) or None if the packet is unusable
    (this is the point at which a low-confidence / corrupted observation
    becomes an erasure, per Sec. 7 of the spec)."""
    if len(data) < 4:
        return None
    body, crc_bytes = data[:-4], data[-4:]
    if zlib.crc32(body) & 0xFFFFFFFF != int.from_bytes(crc_bytes, "big"):
        return None
    br = BitReader(body)
    if br.read(12) != MAGIC:
        return None
    version = br.read(4)
    if version != VERSION:
        return None
    symbol_id = br.read(32)
    packet_id = br.read(16)
    layer = br.read(2)
    degree = br.read(6)
    flags = br.read(6)
    paylen = br.read(12)
    br.align()
    start = br.bitpos // 8
    payload = body[start:start + paylen]
    if len(payload) != paylen:
        return None
    return PacketHeader(symbol_id, packet_id, layer, degree, flags), payload
