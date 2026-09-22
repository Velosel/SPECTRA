import random
from spectra.codec import SpectraEncoder, SpectraDecoder
from spectra.channel import simulate_channel

PAYLOAD = bytes(random.Random(1).randbytes(600))  # ~ typical serialized JSON/ID payload size
TRIALS = 200


def trial(loss_rate, corrupt_rate, rng):
    enc = SpectraEncoder(PAYLOAD, symbol_id=0xC0FFEE)
    packets = enc.generate_packets()
    observed = simulate_channel(packets, loss_rate, corrupt_rate, rng)
    dec = SpectraDecoder()
    for p in observed:
        dec.feed(p)
    layer, _ = dec.result()
    return layer, len(packets)


def sweep():
    print(f"{'loss':>6} {'L2 (full)':>10} {'L1 (essential)':>15} {'L0 (id only)':>13} {'none':>6}   avg_packets")
    for loss in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
        rng = random.Random(42)
        counts = {"L2": 0, "L1": 0, "L0": 0, "NONE": 0}
        npkt = 0
        for _ in range(TRIALS):
            layer, n = trial(loss, 0.02, rng)
            counts[layer] += 1
            npkt = n
        row = " ".join(f"{counts[k] / TRIALS:>10.0%}" if k == "L2"
                        else f"{counts[k] / TRIALS:>15.0%}" if k == "L1"
                        else f"{counts[k] / TRIALS:>13.0%}" if k == "L0"
                        else f"{counts[k] / TRIALS:>6.0%}"
                        for k in ("L2", "L1", "L0", "NONE"))
        print(f"{loss:>6.0%} {row}   {npkt}")


if __name__ == "__main__":
    print(f"payload={len(PAYLOAD)} bytes, {TRIALS} trials/point\n")
    sweep()
