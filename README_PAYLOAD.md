# SPECTRA v0.8 — Payload Mode

This is the image-only payload version.

## Fixed canvas

Every symbol is:

```text
720 × 720 pixels
```

## Write a payload yourself

```powershell
python spectra_payload.py encode --payload "Hello from SPECTRA!"
```

The image is created at:

```text
outputs\spectra_720.png
```

## Decode it

```powershell
python spectra_payload.py decode outputs\spectra_720.png
```

The decoder reports:

- packet count / CRC-valid packets
- recovered layer
- recovered payload
- payload byte count
- SHA-256
- verification status

## Use a file as the payload

```powershell
python spectra_payload.py encode --payload-file myfile.txt --output outputs\myfile_spectra.png
```

Binary files are supported too:

```powershell
python spectra_payload.py encode --payload-file image.bin --output outputs\image_spectra.png
```

## Interactive mode

```powershell
python spectra_payload.py interactive
```

Type several lines of text and finish with an empty line.

The program then:

1. encodes the payload;
2. creates the 720x720 SPECTRA image;
3. decodes the same image;
4. verifies the SHA-256;
5. prints the recovered payload.

## Automated test

```powershell
python test_payload.py
```

Expected:

```text
L2
Verified: True
ROUND-TRIP: PASS
```

No camera or webcam is involved in this stage.


## Easy structured payload

Instead of writing JSON manually:

```powershell
python spectra_payload.py encode `
  --id SKU-88213 `
  --batch A19 `
  --url "https://example.com/p/88213"
```

This automatically creates:

```json
{"id":"SKU-88213","batch":"A19","url":"https://example.com/p/88213"}
```

and encodes it.

## Dense 720x720 mode

The default is now:

```text
252 real coded packets
```

which fills the available packet-region field instead of leaving large empty areas.

## Interactive structured mode

```powershell
python spectra_payload.py interactive
```

Then:

```text
ID: SKU-88213
Batch: A19
URL: https://example.com/p/88213
```

The generated payload is automatically compact JSON.
