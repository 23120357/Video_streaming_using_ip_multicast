import sys
import socket
import time
import math
from VideoStream import VideoStream
from CustomPacket import CustomPacket

MULTICAST_ADDR = "239.1.1.1"
MULTICAST_PORT = 5004
MAX_PAYLOAD_SIZE = 1400

class MulticastServer:
    def __init__(self, filename):
        try:
            self.videoStream = VideoStream(filename)
        except IOError:
            print(f"Error: Cannot open video file '{filename}'")
            sys.exit(1)
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.seqNum = 0
        self.frame_count = 0

    def start(self):
        print(f"Server started. Multicasting to {MULTICAST_ADDR}:{MULTICAST_PORT}...")
        
        try:
            while True:
                start_time = time.time()
                
                # Read the next frame
                frame_data = self.videoStream.nextFrame()
                if frame_data is None:
                    # If nextFrame returns None even after EOF loop attempt, break
                    print("Reached end of video stream or failed to read.")
                    break
                
                self.frame_count += 1
                self.sendFrame(frame_data)
                
                # Control frame rate to approx 20 FPS (50ms per frame)
                elapsed = time.time() - start_time
                sleep_time = max(0.001, 0.05 - elapsed)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\nServer shutting down...")
        finally:
            self.sock.close()
            print("Server socket closed.")

    def sendFrame(self, frame_data):
        total_len = len(frame_data)
        total_frags = math.ceil(total_len / MAX_PAYLOAD_SIZE)
        # Create a timestamp based on current time (milliseconds)
        timestamp = int(time.time() * 1000) & 0xFFFFFFFF
        
        # Log frame details
        print(f"[TX Frame {self.frame_count}] Size: {total_len} bytes, Timestamp: {timestamp}, Fragments: {total_frags}")
        
        for idx in range(total_frags):
            start = idx * MAX_PAYLOAD_SIZE
            chunk = frame_data[start : start + MAX_PAYLOAD_SIZE]
            
            # Encode packet
            packet_obj = CustomPacket()
            packet_data = packet_obj.encode(
                timestamp=timestamp,
                seqnum=self.seqNum,
                frag_idx=idx,
                total_frags=total_frags,
                payload=chunk
            )
            
            # Send packet to multicast group
            try:
                self.sock.sendto(packet_data, (MULTICAST_ADDR, MULTICAST_PORT))
            except Exception as e:
                print(f"Error sending packet seq {self.seqNum}: {e}")
                
            self.seqNum = (self.seqNum + 1) & 0xFFFF

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("[Usage: python Server.py <file>.Mjpeg]\n")
        sys.exit(1)
        
    filename = sys.argv[1]
    server = MulticastServer(filename)
    server.start()