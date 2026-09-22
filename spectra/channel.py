"""Stand-in for the optical channel model in Sec. 7/10 (Y = C(X) + N + E).
loss_rate models packets a real vision pipeline would never detect/extract
(occlusion, extreme blur -> confidence below tau_L). corrupt_rate models
packets that get sampled but decode to the wrong bits (caught by CRC-32,
so they become erasures too -- this is the "candidate rejected" path)."""
import random


def simulate_channel(packets, loss_rate: float = 0.3, corrupt_rate: float = 0.05,
                      rng: random.Random = None):
    rng = rng or random.Random()
    observed = []
    for p in packets:
        if rng.random() < loss_rate:
            continue
        if rng.random() < corrupt_rate:
            p = bytearray(p)
            i = rng.randrange(len(p))
            p[i] ^= 0xFF
            p = bytes(p)
        observed.append(p)
    rng.shuffle(observed)  # camera doesn't see packets in transmission order
    return observed
