# This lone function sends a message to MoMMI's commloop.
# Useful for copy pasting.


def MoMMI(address, key, type, meta, content):
    import hmac
    import json
    import struct
    from socket import socket, AF_INET, SOCK_STREAM
    from hashlib import sha512

    msg = json.dumps({
        "type": type,
        "meta": meta,
        "cont": content
    }).encode("UTF-8")  # type: bytes
    h = hmac.new(key, msg, sha512)
    packet = b"\x30\x05"  # type: bytes
    packet += h.digest()
    packet += struct.pack("!I", len(msg))
    packet += msg

    with socket(AF_INET, SOCK_STREAM) as s:
        s.settimeout(5)
        s.connect(address)
        s.sendall(packet)
        ret = struct.unpack("!B", s.recv(1))[0]  # type: int
        if ret != 0:
            raise IOError(f"MoMMI returned non-zero code {ret}")

def derp():
    pass
