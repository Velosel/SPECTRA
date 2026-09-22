from pathlib import Path
from spectra.codec import SpectraEncoder
from spectra.render import _safe_packet_regions, _packet_interleave
from spectra.render import render_symbol

enc = SpectraEncoder(b"SPECTRA validation payload", symbol_id=0x1234ABCD)
packets = enc.generate_packets(target_packets=160)
out = Path("outputs/validation.png")
render_symbol(packets, enc.symbol_id, size=720, out_path=str(out), center_lines=["A","B","C"])
assert out.exists()
print(f"Render validation: PASS ({len(packets)} real coded packets) -> {out}")
