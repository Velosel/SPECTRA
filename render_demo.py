from __future__ import annotations
import argparse
from pathlib import Path
from spectra.codec import SpectraEncoder
from spectra.render import render_symbol

PAYLOAD = b'{"id":"SKU-88213","batch":"A19","url":"https://example.com/p/88213"}'

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",default="outputs/spectra_reversible.png")
    ap.add_argument("--size",type=int,default=720)
    ap.add_argument("--title",default="SPECTRA")
    ap.add_argument("--lines",default="CONNECT|SHARE|EXPLORE|V.R.V.|2026")
    ap.add_argument("--packets",type=int,default=160)
    args=ap.parse_args()

    enc=SpectraEncoder(PAYLOAD,symbol_id=0x1234ABCD,block_size=4,redundancy=1.6)
    packets=enc.generate_packets(target_packets=args.packets)
    lines=[x.strip() for x in args.lines.split("|") if x.strip()]

    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)

    print(f"Encoded {len(PAYLOAD)} bytes into {len(packets)} real packets.")
    print(f"K={enc.K}, K1={enc.K1}, block_size={enc.block_size}")

    render_symbol(
        packets,
        symbol_id=enc.symbol_id,
        meta_lines=lines,
        size=args.size,
        out_path=str(out),
        center_title=args.title,
        center_lines=lines,
    )
    print(f"Saved {out.resolve()}")
