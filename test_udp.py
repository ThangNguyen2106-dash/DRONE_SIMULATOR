import socket

PORT = 14551

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("0.0.0.0", PORT))
s.setblocking(False)

print(f"UDP RX socket OK: 0.0.0.0:{PORT}")
print("Press Ctrl+C to exit.")

try:
    while True:
        try:
            data, addr = s.recvfrom(4096)
            print("RX", addr, len(data), "bytes")
        except BlockingIOError:
            pass
except KeyboardInterrupt:
    pass
finally:
    s.close()
