# SPECTRA v0.6 — Reversible Image Mode

This version keeps the PDF-aligned packet protocol and makes the visual PNG
directly reversible.

Each physical packet region encodes the serialized packet bytes using the
16-color alphabet:

    4 bits / color module

Current image profile:

- 160 real coded packets
- 4-bit, 16-color visual alphabet
- 4-byte fountain source blocks
- 12 fragmented L0 metadata packets
- packet header + payload + CRC-32 encoded in every region
- deterministic spatial interleaver
- collision-free packet regions
- central text panel and four anchors

## Generate

```powershell
python render_demo.py --packets 160
```

## Decode the PNG directly

```powershell
python image_decode.py outputs\spectra_reversible.png
```

Expected result:

```text
layer: L2
crc_valid_packets: ...
verified: True
payload: {"id":"SKU-88213","batch":"A19","url":"https://example.com/p/88213"}
```

No camera, homography, webcam, or OCR is involved in this mode.

## Important

The previous dense renderer was a visualization-only renderer: module colors
were derived from packet hashes and therefore were not reversibly decodable.
v0.6 fixes that by encoding the actual packet bytes into the color modules.
