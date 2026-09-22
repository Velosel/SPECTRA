from __future__ import annotations
from pathlib import Path
import hashlib

from spectra_payload import encode_payload, decode_payload

TEST_PAYLOAD = (
    "SPECTRA payload test.\n"
    "This is user-entered application data.\n"
    "Line 3: spatial packets + FEC + SHA-256.\n"
)

out = Path("outputs/test_payload_720.png")
meta = encode_payload(
    TEST_PAYLOAD.encode("utf-8"),
    str(out),
    ["PAYLOAD", "TEXT TEST", "720x720", "SPECTRA V0.7"]
)

result = decode_payload(str(out))

print("=== AUTOMATED PAYLOAD TEST ===")
print("Original SHA-256:", meta["sha256"])
print("Decoded SHA-256: ", result["sha256"])
print("Layer:           ", result["layer"])
print("CRC-valid:       ", result["crc_valid_packets"])
print("Verified:        ", result["verified"])
print("Recovered:       ", repr(result.get("payload")))

assert result["layer"] == "L2"
assert result["verified"] is True
assert result["payload"] == TEST_PAYLOAD
assert result["sha256"] == hashlib.sha256(TEST_PAYLOAD.encode()).hexdigest()

print("ROUND-TRIP: PASS")
