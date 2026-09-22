# SPECTRA

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

**Sp**atially **P**artitioned **E**rror-**C**orrecting **T**opological **R**edundant **A**rray

SPECTRA is a research-grade visual data encoding architecture designed as an alternative to conventional 2D barcodes (QR-style monolithic matrices). Instead of treating a symbol as one dense grid, SPECTRA distributes the encoded payload across independently validated spatial packet regions, each individually error-checked and reconstructable via fountain coding.

This repository is the **reference codec**: a working encoder/decoder for the packet format, FEC layer, and confidence/erasure decoding policy described in the SPECTRA paper. It runs on real bytes and renders real symbols — not a mockup.

---

## Table of contents

- [Core architecture](#core-architecture)
- [Requirements](#requirements)
- [Quick start](#quick-start)
- [Project structure](#project-structure)
- [Implemented from the spec](#implemented-from-the-spec)
- [Deliberately not implemented](#deliberately-not-implemented-out-of-scope-for-this-pass)
- [Rendering profile](#current-rendering-profile)
- [Roadmap](#roadmap)
- [License](#license)

---

## Core architecture

| | Feature | Description |
|---|---|---|
| 🌈 | **16-color visual alphabet** | Each module encodes 4 bits. |
| 📦 | **Spatial packetization** | Payload is split across independent visual regions. |
| 🔄 | **Fountain/FEC coding** | Redundant packets allow recovery after packet loss. |
| 🧩 | **Progressive payload layers** | L0 / L1 / L2 enable staged information recovery. |
| 🔐 | **CRC-32 validation** | Corrupted packets are rejected locally, per-packet. |
| 🧾 | **SHA-256 integrity verification** | The fully reconstructed payload is cryptographically verified. |
| 🎯 | **Four anchor structures** | Deterministic symbol geometry, for future camera-based decoding. |
| 🚫 | **Collision-free rendering** | Visual modules stay inside their assigned regions — no overlap. |
| 🖼️ | **720×720 reference profile** | Optimized for the current image-based research implementation. |

### How decoding degrades gracefully

SPECTRA's layered design means a decoder always returns the **highest layer it can verify**, rather than failing outright:

```
L2 (full payload, fountain-coded)  ──▶  best case, everything recovered
        │  falls back if too many packets lost
        ▼
L1 (essential prefix, fountain-coded)  ──▶  partial payload, still verified
        │  falls back if L1 also unrecoverable
        ▼
L0 (small repeated record: SHA-256 digest + shape, no FEC needed)
        │
        ▼
   none (nothing verifiable)
```

This is the core claim benchmarked in `benchmark.py`: success degrades gracefully as loss increases, rather than dropping off a cliff.

---

## Requirements

- Python 3.8+
- Only the standard library is required for the codec itself (bitstream, packet framing, LT fountain code, channel simulation).
- `render_demo.py` produces a PNG symbol and may require an image library (e.g. `Pillow`) depending on your environment — install it if `render_demo.py` reports a missing import:

```bash
pip install Pillow
```

*(Adjust the above if your environment already pins dependencies in a `requirements.txt` / `pyproject.toml`.)*

---

## Quick start

```bash
git clone <repo-url>
cd spectra
python3 demo.py        # single payload, several loss rates, prints recovered layer
python3 benchmark.py   # 200-trial sweep of loss rate -> L2/L1/L0/none success rate
python3 render_demo.py # encodes a payload and renders the actual packets to a PNG symbol
```

To render with a specific number of real coded packets:

```bash
python3 render_demo.py --packets 160
```

Higher packet counts increase visual redundancy and repair overhead — this is a research parameter, not a universally optimal setting.

---

## Project structure

```
spectra/
├── bitstream.py   # Bit-exact writer/reader for the non-byte-aligned header
├── packet.py      # Packs/unpacks Table 1's header (MAGIC/VERSION/SYMBOL-ID/
│                  #   PACKET-ID/LAYER/DEGREE/FLAGS/PAYLOAD-LEN/PAYLOAD/CRC-32)
├── lt_code.py     # Luby Transform fountain code: robust-soliton degree
│                  #   distribution, encoder, belief-propagation (peeling) decoder
├── codec.py       # SpectraEncoder / SpectraDecoder — 3-layer progressive model
├── channel.py     # Erasure/corruption channel simulator (stand-in for the
│                  #   optical channel)
└── render.py      # Dense forward renderer: 4 anchors + center panel +
                    #   non-overlapping packet regions
demo.py             # Single-payload, multi-loss-rate demo
benchmark.py        # 200-trial loss-rate sweep
render_demo.py      # Encodes + renders a payload to a PNG symbol
```

**Key implementation notes:**

- `packet.py` — CRC failure or a bad `MAGIC` value returns `None`; this **is** the erasure decision at the packet level.
- `lt_code.py` — Neighbor indices are derived from `(seed, packet_id)` via a seeded PRNG rather than transmitted, matching the paper's "coding neighborhood `A_i`" (Sec. 6.1).
- `codec.py` — Implements the 3-layer progressive model (Sec. 5). Decoder reconstructs the highest layer it can verify (Algorithm 2, steps 21–29).
- `render.py` — Each logical region `Ω_i` contains one packet glyph made of deterministic multi-color micro-modules. Regions are disjoint and never cross the protected anchors, center panel, or border.

---

## Implemented from the spec

- Bit-exact packet header per Table 1, with local CRC-32 validation.
- Fountain-coded (LT) payload reconstruction, decoupled per layer.
- Progressive L0/L1/L2 decoding, returning the highest verified layer.
- End-to-end SHA-256 integrity check on full-payload (L2) reconstruction.
- Deterministic neighbor-index derivation from `packet_id` and the symbol/layer FEC seed, while the on-wire `DEGREE` remains the 6-bit coding metadata field.
- Deterministic keyed spatial interleaver `π` for packet placement.
- A measurable erasure-channel benchmark reproducing the paper's core claim shape: success degrades gracefully L2 → L1 → L0 → none as loss increases (see `benchmark.py` output).

## Deliberately not implemented (out of scope for this pass)

- **Vision pipeline** (Sec. 8) — anchor detection, homography estimation, rectification, blur/contrast feature extraction. `channel.py`'s `loss_rate` / `corrupt_rate` stand in for "packet never reached confidence threshold" / "packet failed CRC after sampling"; no image processing happens here.
- **Confidence scoring formula** (Sec. 7, `q_i = w_g g_i + ...`) — collapsed into the channel's `corrupt_rate` for now. The three-state trusted/candidate/erasure policy isn't modeled separately from CRC pass/fail.
- **Reverse (image-to-packet) rendering path** — `render.py` implements the forward direction only, with a deterministic keyed packet interleaver and collision-free packet regions. It does not yet optimize `J(π)` for a measured occlusion model.
- **RaptorQ** — the spec allows a simplified fountain model (Sec. 6.1); this implementation uses plain LT, not standardized RaptorQ. LT has a known small-`K` overhead cost, visible in the benchmark as <100% L2 success even at 0% loss for `K≈13`. Confirmed by testing: raising `redundancy` from 1.6 to 2.5 closes that gap to 100%. A RaptorQ backend would need less overhead for the same `K`; swapping it in only touches `lt_code.py`.
- **Digital signature / MAC** (Sec. 14) — only CRC-32 + SHA-256 digest; no authentication.

---

## Current rendering profile

The reference renderer defaults to a dense **160-packet** symbol for the demo. These are real SPECTRA packets, not decorative filler — additional packets beyond the essential set are L2 fountain repair symbols, consistent with the paper's target packet count `N`.

The renderer uses disjoint packet regions `Ω_i`. Each `Ω_i` contains one collision-free 3×3 visual packet glyph. The glyph never crosses its region, the outer border, the anchor zones, or the center panel.

---

## Roadmap

Rough ordering, based on what's marked "not implemented" above:

1. Vision pipeline (anchor detection → homography → rectification) to close the reverse image-to-packet path.
2. Confidence scoring (Sec. 7) as a distinct trusted/candidate/erasure policy, rather than folding it into `corrupt_rate`.
3. Optional RaptorQ backend for lower small-`K` overhead.
4. Digital signature / MAC layer (Sec. 14) for authenticated payloads.

---

## License

*Not yet specified — add a `LICENSE` file and reference it here before distributing.*

## Citation

If this codec is used alongside the SPECTRA paper, cite the paper directly. *(Add citation details here once available.)*
