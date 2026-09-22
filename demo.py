import random
from spectra.codec import SpectraEncoder, SpectraDecoder
from spectra.channel import simulate_channel

PAYLOAD = b'{"id":"SKU-88213","batch":"A19","url":"https://example.com/p/88213"}'


def run(loss_rate, corrupt_rate, seed):
    enc = SpectraEncoder(PAYLOAD, symbol_id=0x1234ABCD)
    packets = enc.generate_packets(target_packets=96)
    observed = simulate_channel(packets, loss_rate, corrupt_rate, random.Random(seed))

    dec = SpectraDecoder()
    for p in observed:
        dec.feed(p)
    layer, data = dec.result()

    print(f"loss={loss_rate:.0%} corrupt={corrupt_rate:.0%}  "
          f"sent={len(packets):3d} observed={len(observed):3d}  -> {layer}")
    if layer == "L2":
        print(f"  full payload recovered & hash-verified: {data}")
    elif layer == "L1":
        print(f"  essential-only partial recovery ({len(data)} bytes): {data[:32]}...")
    elif layer == "L0":
        print(f"  recognition only: K={dec.meta['K']} blocks, "
              f"{dec.meta['payload_len']} byte payload, digest known")
    else:
        print("  symbol not detected at all")
    return layer


if __name__ == "__main__":
    print(f"Original payload ({len(PAYLOAD)} bytes): {PAYLOAD}\n")
    for loss in (0.0, 0.3, 0.55, 0.75, 0.9):
        run(loss, corrupt_rate=0.03, seed=7)
