"""Bit-level writer/reader used to pack the SPECTRA packet header, whose
fields (12/4/32/16/2/6/6/12 bits) are not byte-aligned."""


class BitWriter:
    def __init__(self):
        self._out = bytearray()
        self._acc = 0
        self._nbits = 0

    def write(self, value: int, width: int) -> None:
        if value < 0 or value >= (1 << width):
            raise ValueError(f"value {value} does not fit in {width} bits")
        self._acc = (self._acc << width) | value
        self._nbits += width
        while self._nbits >= 8:
            self._nbits -= 8
            self._out.append((self._acc >> self._nbits) & 0xFF)
        self._acc &= (1 << self._nbits) - 1 if self._nbits else 0

    def align(self) -> None:
        if self._nbits:
            self.write(0, 8 - self._nbits)

    def getvalue(self) -> bytes:
        return bytes(self._out)


class BitReader:
    def __init__(self, data: bytes):
        self._data = data
        self.bitpos = 0

    def read(self, width: int) -> int:
        val = 0
        for _ in range(width):
            byte = self._data[self.bitpos >> 3]
            bit = (byte >> (7 - (self.bitpos & 7))) & 1
            val = (val << 1) | bit
            self.bitpos += 1
        return val

    def align(self) -> None:
        rem = self.bitpos & 7
        if rem:
            self.bitpos += 8 - rem
