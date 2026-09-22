from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path

from spectra.codec import SpectraEncoder
from spectra.render import render_symbol
from image_decode import decode_image

CANVAS = 720
DEFAULT_PACKETS = 252

def encode_payload(payload: bytes, output: str, center_lines: list[str], packets: int = DEFAULT_PACKETS) -> dict:
    # Small fixed source block keeps each packet compact enough for the
    # 720x720 reversible visual profile.
    encoder = SpectraEncoder(
        payload,
        symbol_id=int.from_bytes(hashlib.sha256(payload).digest()[:4], "big"),
        block_size=4,
        redundancy=1.6,
    )

    packets = encoder.generate_packets(target_packets=packets)

    meta = {
        "version": 7,
        "canvas": [CANVAS, CANVAS],
        "packet_count": len(packets),
        "payload_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "encoding": "UTF-8" if _is_utf8(payload) else "BASE64_BINARY",
    }

    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Human-readable center text is separate from machine payload.
    if not center_lines:
        center_lines = ["PAYLOAD", f"{len(payload)} BYTES", "SHA-256 VERIFIED"]

    render_symbol(
        packets,
        symbol_id=encoder.symbol_id,
        meta_lines=center_lines,
        size=CANVAS,
        out_path=str(out),
        center_title="SPECTRA",
        center_lines=center_lines,
    )

    Path(str(out) + ".json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    return meta

def decode_payload(image: str) -> dict:
    result = decode_image(image, size=CANVAS)
    return result

def _is_utf8(data: bytes) -> bool:
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False

def main():
    ap = argparse.ArgumentParser(
        description="SPECTRA v0.8 — 720x720 payload encoder/decoder"
    )
    sub = ap.add_subparsers(dest="command")

    enc = sub.add_parser("encode", help="Encode a payload into a 720x720 SPECTRA image")
    enc.add_argument("--payload", help="Payload text")
    enc.add_argument("--payload-file", help="Read raw payload bytes from a file")
    enc.add_argument("--output", default="outputs/spectra_720.png")
    enc.add_argument("--packets", type=int, default=DEFAULT_PACKETS)
    enc.add_argument(
        "--center",
        default="PAYLOAD|SPECTRA V0.8|720x720",
        help="Center lines separated by |"
    )
    enc.add_argument("--id", dest="item_id", help="Convenient JSON id field")
    enc.add_argument("--batch", help="Convenient JSON batch field")
    enc.add_argument("--url", help="Convenient JSON url field")

    dec = sub.add_parser("decode", help="Decode a 720x720 SPECTRA image")
    dec.add_argument("image")

    interactive = sub.add_parser(
        "interactive",
        help="Type a payload and immediately encode + decode it"
    )
    interactive.add_argument("--output", default="outputs/spectra_720.png")

    args = ap.parse_args()

    if args.command == "encode":
        if args.payload_file:
            payload = Path(args.payload_file).read_bytes()
        elif args.item_id or args.batch or args.url:
            obj = {}
            if args.item_id is not None:
                obj["id"] = args.item_id
            if args.batch is not None:
                obj["batch"] = args.batch
            if args.url is not None:
                obj["url"] = args.url
            payload = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        elif args.payload is not None:
            payload = args.payload.encode("utf-8")
        else:
            payload = input("Enter SPECTRA payload: ").encode("utf-8")

        center = [x.strip() for x in args.center.split("|") if x.strip()]
        meta = encode_payload(payload, args.output, center, packets=args.packets)

        print("\n=== SPECTRA ENCODE ===")
        print(f"Canvas:       {CANVAS}x{CANVAS}")
        print(f"Payload:      {meta['payload_bytes']} bytes")
        print(f"Packets:      {meta['packet_count']}")
        print(f"SHA-256:      {meta['sha256']}")
        print(f"Encoding:     {meta['encoding']}")
        print(f"Image:        {Path(args.output).resolve()}")
        return

    if args.command == "decode":
        result = decode_payload(args.image)

        print("\n=== SPECTRA DECODE ===")
        print(f"Canvas:       {CANVAS}x{CANVAS}")
        print(f"Regions:      {result.get('regions')}")
        print(f"CRC-valid:    {result.get('crc_valid_packets')}")
        print(f"Layer:        {result.get('layer')}")
        print(f"Verified:     {result.get('verified')}")

        if result.get("payload") is not None:
            print(f"Payload:      {result['payload']}")
            print(f"Payload bytes: {result['payload_bytes']}")
            print(f"SHA-256:      {result['sha256']}")
        elif result.get("payload_preview"):
            print(f"Payload preview: {result['payload_preview']}")
        return

    if args.command == "interactive":
        print("=== SPECTRA INTERACTIVE 720x720 / V0.8 ===")
        print("Press Enter on an empty ID to use free-form payload mode.")
        item_id = input("ID: ").strip()
        if item_id:
            batch = input("Batch: ").strip()
            url = input("URL: ").strip()
            obj = {"id": item_id}
            if batch:
                obj["batch"] = batch
            if url:
                obj["url"] = url
            payload = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            center = ["PAYLOAD", "ID/BATCH/URL", "SPECTRA V0.8"]
        else:
            print("Enter your free-form payload. Finish with an empty line.")
            lines = []
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
            payload = "\n".join(lines).encode("utf-8")
            center = ["PAYLOAD", f"{len(payload)} BYTES", "SPECTRA V0.8"]

        meta = encode_payload(
            payload,
            args.output,
            center,
            packets=DEFAULT_PACKETS
        )

        print("\nEncoded.")
        print(f"Image: {Path(args.output).resolve()}")

        result = decode_payload(args.output)

        print("\nDecoded.")
        print(f"Layer:    {result.get('layer')}")
        print(f"Verified: {result.get('verified')}")
        print(f"SHA-256:  {result.get('sha256')}")

        if result.get("payload") is not None:
            print("\nRecovered payload:")
            print(result["payload"])

            original_hash = meta["sha256"]
            recovered_hash = result["sha256"]

            if original_hash == recovered_hash:
                print("\nROUND-TRIP: PASS")
            else:
                print("\nROUND-TRIP: FAIL")
        return

    ap.print_help()

if __name__ == "__main__":
    main()
