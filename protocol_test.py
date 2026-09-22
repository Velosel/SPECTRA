from spectra.packet import PacketHeader, pack_packet, unpack_packet, MAGIC, VERSION

h = PacketHeader(0x12345678, 0x002A, layer=2, degree=17, flags=3)
payload = b"SPECTRA-PDF-TABLE-1"
blob = pack_packet(h, payload)
res = unpack_packet(blob)
assert res is not None
h2, p2 = res
assert h2.symbol_id == h.symbol_id
assert h2.packet_id == h.packet_id
assert h2.layer == h.layer
assert h2.degree == h.degree
assert h2.flags == h.flags
assert p2 == payload
assert MAGIC == 0xA5C
assert VERSION == 1
print("PDF packet Table 1 conformance: PASS")
