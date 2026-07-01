import struct

HEADER_SIZE = 12

class CustomPacket:
    def __init__(self):
        self.header = bytearray(HEADER_SIZE)
        self.payload = b""

    def encode(self, timestamp, seqnum, frag_idx, total_frags, payload):
        """
        Encodes a custom packet with a 12-byte header.
        Format:
          - Timestamp / Frame ID: 4 bytes (unsigned int)
          - Sequence Number: 2 bytes (unsigned short)
          - Fragment Index: 2 bytes (unsigned short)
          - Total Fragments: 2 bytes (unsigned short)
          - Payload Size: 2 bytes (unsigned short)
        """
        self.payload = payload
        # Header size is 12 bytes
        self.header = struct.pack(
            "!IHHHH",
            timestamp & 0xFFFFFFFF,
            seqnum & 0xFFFF,
            frag_idx & 0xFFFF,
            total_frags & 0xFFFF,
            len(payload) & 0xFFFF
        )
        return self.header + self.payload

    def decode(self, byteStream):
        """
        Decodes a custom packet from a raw byte stream.
        """
        if len(byteStream) < HEADER_SIZE:
            raise ValueError("Packet is too short to contain a valid header.")
        self.header = byteStream[:HEADER_SIZE]
        self.payload = byteStream[HEADER_SIZE:]

    def timestamp(self):
        """Return frame timestamp / ID."""
        val = struct.unpack("!I", self.header[0:4])[0]
        return int(val)

    def seqNum(self):
        """Return global packet sequence number."""
        val = struct.unpack("!H", self.header[4:6])[0]
        return int(val)

    def fragmentIndex(self):
        """Return fragment index."""
        val = struct.unpack("!H", self.header[6:8])[0]
        return int(val)

    def totalFragments(self):
        """Return total fragments for this frame."""
        val = struct.unpack("!H", self.header[8:10])[0]
        return int(val)

    def payloadSize(self):
        """Return payload size in bytes."""
        val = struct.unpack("!H", self.header[10:12])[0]
        return int(val)

    def getPayload(self):
        """Return payload content."""
        return self.payload

    def getPacket(self):
        """Return entire raw packet (header + payload)."""
        return self.header + self.payload
