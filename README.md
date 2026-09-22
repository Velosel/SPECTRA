SPECTRA

Spatially Partitioned Error-Correcting Topological Redundant Array

SPECTRA is a research-grade visual data encoding architecture designed as an alternative approach to conventional 2D barcodes. Instead of treating a symbol as a monolithic matrix, SPECTRA distributes encoded payload information across independently validated spatial packet regions.

Core Architecture
🌈 16-color visual alphabet — each module represents 4 bits.
📦 Spatial packetization — payloads are distributed across independent visual regions.
🔄 Fountain/FEC coding — redundant encoding packets enable recovery after packet loss.
🧩 Progressive payload layers — L0, L1 and L2 allow staged information recovery.
🔐 CRC-32 validation — corrupted packets can be rejected locally.
🧾 SHA-256 integrity verification — the reconstructed payload is cryptographically verified.
🎯 Four anchor structures — provide a deterministic symbol geometry for future camera-based decoding.
🚫 Collision-free rendering — visual modules remain inside their assigned regions and do not overlap.
🖼️ 720×720 reference profile — optimized for the current image-based research implementation.

# SPECTRA - reference codec

A working encoder/decoder for the packet format, FEC layer, and
confidence/erasure decoding policy described in the SPECTRA paper. Runs
on real bytes, not a mockup.

## Run it

```
python3 demo.py        # single payload, several loss rates, prints recovered layer
python3 benchmark.py   # 200-trial sweep of loss rate -> L2/L1/L0/none success rate
python3 render_demo.py # encodes a payload and renders the actual packets to a PNG symbol
```

## Files

- `spectra/bitstream.py` — bit-exact writer/reader for the non-byte-aligned header.
- `spectra/packet.py` — packs/unpacks Table 1's header (MAGIC/VERSION/SYMBOL-ID/
  PACKET-ID/LAYER/DEGREE/FLAGS/PAYLOAD-LEN/PAYLOAD/CRC-32). CRC failure or bad
  MAGIC returns `None` — this **is** the erasure decision at the packet level.
- `spectra/lt_code.py` — Luby Transform fountain code: robust-soliton degree
  distribution, encoder, and a belief-propagation (peeling) decoder. Neighbor
  indices are derived from `(seed, packet_id)` via a seeded PRNG rather than
  transmitted, matching the paper's "coding neighborhood A_i" (Sec. 6.1).
- `spectra/codec.py` — `SpectraEncoder`/`SpectraDecoder`. Implements the
  3-layer progressive model (Sec. 5): L0 is a small repeated record (SHA-256
  digest + shape, no FEC needed), L1 is LT-coded over an essential prefix of
  blocks, L2 is LT-coded over the full payload. Decoder reconstructs the
  highest layer it can verify (Algorithm 2, steps 21–29).
- `spectra/channel.py` — erasure/corruption channel simulator standing in
  for the optical channel.
- `spectra/render.py` — dense forward renderer: 4 anchor regions + a center
  panel + non-overlapping packet regions. Each logical region Ω_i contains
  one packet glyph made from deterministic multi-color micro-modules. Regions
  are disjoint and never cross the protected anchors, center panel, or border.

## Implemented from the spec

- Bit-exact packet header per Table 1, with local CRC-32 validation.
- Fountain-coded (LT) payload reconstruction, decoupled per layer.
- Progressive L0/L1/L2 decoding returning the highest verified layer.
- End-to-end SHA-256 integrity check on full-payload (L2) reconstruction.
- Deterministic neighbor-index derivation from packet_id and the symbol/layer
  FEC seed, while the on-wire DEGREE remains the 6-bit coding metadata field.
- Deterministic keyed spatial interleaver π for packet placement.
- A measurable erasure-channel benchmark reproducing the paper's core
  claim shape: success degrades gracefully L2 → L1 → L0 → none as loss
  increases (see `benchmark.py` output).

## Deliberately not implemented (out of scope for this pass)

- **Vision pipeline** (Sec. 8): anchor detection, homography estimation,
  rectification, blur/contrast feature extraction. `channel.py`'s
  `loss_rate`/`corrupt_rate` are a stand-in for "packet never reached
  confidence threshold" / "packet failed CRC after sampling" — no image
  processing happens here.
- **Confidence scoring formula** (Sec. 7, `q_i = w_g g_i + ...`): collapsed
  into the channel's `corrupt_rate` for now. The three-state
  trusted/candidate/erasure policy isn't modeled separately from
  CRC pass/fail.
- **Symbol rendering is implemented** (`spectra/render.py`) in the forward
  direction. The current renderer uses a deterministic keyed packet
  interleaver and collision-free packet regions. It does not yet optimize
  `J(π)` for a measured occlusion model and there is no reverse image-to-packet
  path yet. That requires the geometry/vision pipeline below.
- **RaptorQ**: the spec allows a simplified fountain model (Sec. 6.1);
  this uses plain LT, not standardized RaptorQ. LT has a known small-K
  overhead cost — visible in the benchmark as <100% L2 success even at
  0% loss for K≈13. Confirmed by testing: raising `redundancy` from 1.6
  to 2.5 closes that gap to 100%. A RaptorQ backend would need less
  overhead for the same K; swapping it in only touches `lt_code.py`.
- **Digital signature / MAC** (Sec. 14): only CRC-32 + SHA-256 digest,
  no authentication.

## Current rendering profile

The reference renderer defaults to a dense 160-packet symbol for the demo.
Those are real SPECTRA packets, not decorative filler. Additional packets are
L2 fountain repair symbols, consistent with the paper's target packet count N.

The renderer uses disjoint packet regions Ω_i. Each Ω_i contains one
collision-free 3x3 visual packet glyph. The glyph never crosses its region,
the outer border, the anchor zones, or the center panel.

Run:

```powershell
python render_demo.py
```

Or choose the number of real coded packets explicitly:

```powershell
python render_demo.py --packets 160
```

Higher packet counts increase visual redundancy and repair overhead; they are
therefore a research parameter, not a universally optimal setting.
