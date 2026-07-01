import socket
import struct
import threading
import time
import queue
import io
import sys
from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk

from CustomPacket import CustomPacket

MULTICAST_ADDR = "239.1.1.1"
MULTICAST_PORT = 5004
VIDEO_SIZE = (640, 360)
REASSEMBLY_TIMEOUT = 1.0  # seconds

class MulticastClient:
    def __init__(self, master):
        self.master = master
        self.master.title("Multicast Video Stream Client")
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # UI Styling (Sleek Dark Theme)
        self.bg_color = "#1e1e2e"
        self.fg_color = "#cdd6f4"
        self.accent_green = "#a6e3a1"
        self.accent_red = "#f38ba8"
        self.btn_bg = "#313244"
        
        self.master.configure(bg=self.bg_color, padx=15, pady=15)
        
        # State Variables
        self.is_connected = False
        self.listen_thread = None
        self.watchdog_thread = None
        
        # Statistics Variables
        self.total_packets_received = 0
        self.lost_packets = 0
        self.last_seq = None
        self.rendered_frames = 0
        
        # Reassembly Buffer
        self.reassembly_buffer = {}
        self.buffer_lock = threading.Lock()
        
        # Thread-safe queue for UI frames
        self.frame_queue = queue.Queue(maxsize=30)
        
        # Create Widgets
        self.create_widgets()
        
        # Schedule the UI update loop
        self.master.after(10, self.update_frame_loop)

    def create_widgets(self):
        # 1. Video Display Label
        self.dummy_img = ImageTk.PhotoImage(Image.new("RGB", VIDEO_SIZE, "#11111b"))
        self.video_label = Label(
            self.master, 
            image=self.dummy_img, 
            bg="#11111b", 
            bd=2, 
            relief="solid", 
            highlightbackground="#313244"
        )
        self.video_label.grid(row=0, column=0, columnspan=2, padx=5, pady=5)
        
        # 2. Statistics Panel
        self.stats_frame = Frame(self.master, bg=self.bg_color)
        self.stats_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")
        
        # Left Stats Column
        self.packets_label = Label(
            self.stats_frame, 
            text="Packets Received: 0  |  Lost: 0", 
            fg=self.fg_color, 
            bg=self.bg_color, 
            font=("Segoe UI", 11)
        )
        self.packets_label.pack(side=LEFT, padx=10)
        
        # Right Stats Column
        self.loss_rate_label = Label(
            self.stats_frame, 
            text="Loss Rate: 0.0%  |  Frames: 0", 
            fg=self.fg_color, 
            bg=self.bg_color, 
            font=("Segoe UI", 11)
        )
        self.loss_rate_label.pack(side=RIGHT, padx=10)
        
        # 3. Control Panel (Buttons)
        self.control_frame = Frame(self.master, bg=self.bg_color)
        self.control_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")
        
        self.join_btn = Button(
            self.control_frame,
            text="Join Stream",
            width=18,
            font=("Segoe UI", 10, "bold"),
            bg=self.btn_bg,
            fg=self.accent_green,
            activebackground=self.accent_green,
            activeforeground=self.bg_color,
            relief="flat",
            bd=0,
            padx=10,
            pady=8,
            command=self.join_stream
        )
        self.join_btn.pack(side=LEFT, expand=True, padx=10)
        
        self.leave_btn = Button(
            self.control_frame,
            text="Leave & Exit",
            width=18,
            font=("Segoe UI", 10, "bold"),
            bg=self.btn_bg,
            fg=self.accent_red,
            activebackground=self.accent_red,
            activeforeground=self.bg_color,
            relief="flat",
            bd=0,
            padx=10,
            pady=8,
            command=self.on_close
        )
        self.leave_btn.pack(side=RIGHT, expand=True, padx=10)

    def join_stream(self):
        if self.is_connected:
            return
        
        try:
            # Set up Multicast Socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind to port (empty string allows listening on all interfaces)
            self.sock.bind(('', MULTICAST_PORT))
            
            # Request to join the multicast group
            mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_ADDR), socket.INADDR_ANY)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            self.sock.settimeout(0.5)
            
            self.is_connected = True
            self.join_btn.config(state=DISABLED, bg="#181825", fg="#585b70")
            
            # Reset counters
            self.total_packets_received = 0
            self.lost_packets = 0
            self.last_seq = None
            self.rendered_frames = 0
            with self.frame_queue.mutex:
                self.frame_queue.queue.clear()
            
            # Start receiver thread
            self.listen_thread = threading.Thread(target=self.listen_multicast, daemon=True)
            self.listen_thread.start()
            
            # Start buffer cleaner thread
            self.watchdog_thread = threading.Thread(target=self.watchdog_cleaner, daemon=True)
            self.watchdog_thread.start()
            
            print(f"Joined multicast group {MULTICAST_ADDR}:{MULTICAST_PORT}")
            
        except Exception as e:
            tkinter.messagebox.showerror("Error", f"Failed to join multicast stream: {e}")

    def leave_stream(self):
        if not self.is_connected:
            return
        
        self.is_connected = False
        
        # Stop receiver thread by closing socket or dropping membership
        try:
            mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_ADDR), socket.INADDR_ANY)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
            self.sock.close()
        except:
            pass
            
        self.join_btn.config(state=NORMAL, bg=self.btn_bg, fg=self.accent_green)
        
        # Clear UI image to blank
        self.video_label.configure(image=self.dummy_img)
        self.video_label.image = self.dummy_img
        print("Left multicast group.")

    def listen_multicast(self):
        while self.is_connected:
            try:
                # Max payload size + header size (1400 + 12) + headroom
                data, addr = self.sock.recvfrom(2048)
                if not data:
                    continue
                
                packet = CustomPacket()
                packet.decode(data)
                
                # Extract fields
                ts = packet.timestamp()
                seq = packet.seqNum()
                frag_idx = packet.fragmentIndex()
                total_frags = packet.totalFragments()
                payload = packet.getPayload()
                
                # Loss Detection
                if self.last_seq is not None:
                    expected = (self.last_seq + 1) & 0xFFFF
                    if seq != expected:
                        # Handle wrapping
                        diff = (seq - expected) & 0xFFFF
                        if diff < 32768:  # sequence number jumped forward
                            self.lost_packets += diff
                    self.last_seq = seq
                else:
                    self.last_seq = seq
                
                self.total_packets_received += 1
                
                # Reassembly logic
                with self.buffer_lock:
                    if ts not in self.reassembly_buffer:
                        self.reassembly_buffer[ts] = {
                            'fragments': {},
                            'total_frags': total_frags,
                            'arrived': time.time()
                        }
                    
                    entry = self.reassembly_buffer[ts]
                    entry['fragments'][frag_idx] = payload
                    
                    # Check if all fragments of the frame have arrived
                    if len(entry['fragments']) == total_frags:
                        # Ensure we have all indexes from 0 to total_frags-1
                        indices = sorted(entry['fragments'].keys())
                        if indices == list(range(total_frags)):
                            assembled_frame = b''.join(entry['fragments'][i] for i in range(total_frags))
                            
                            # Put into the render queue (non-blocking write)
                            try:
                                self.frame_queue.put_nowait(assembled_frame)
                            except queue.Full:
                                # If queue is full, discard oldest to maintain real-time playback
                                try:
                                    self.frame_queue.get_nowait()
                                    self.frame_queue.put_nowait(assembled_frame)
                                except:
                                    pass
                            
                            # Clean up buffer entry
                            del self.reassembly_buffer[ts]
                            
            except socket.timeout:
                continue
            except Exception as e:
                # Socket might have been closed by main thread
                if not self.is_connected:
                    break
                print(f"Error receiving data: {e}")
                time.sleep(0.1)

    def watchdog_cleaner(self):
        """Periodically cleans up incomplete frames that are stale to prevent memory leak."""
        while self.is_connected:
            time.sleep(0.5)
            now = time.time()
            with self.buffer_lock:
                stale_ts = [
                    ts for ts, entry in self.reassembly_buffer.items()
                    if now - entry['arrived'] > REASSEMBLY_TIMEOUT
                ]
                for ts in stale_ts:
                    del self.reassembly_buffer[ts]

    def update_frame_loop(self):
        """GUI Loop that pulls assembled frames and renders them."""
        try:
            if not self.frame_queue.empty():
                frame_data = self.frame_queue.get_nowait()
                
                image_stream = io.BytesIO(frame_data)
                img = Image.open(image_stream)
                
                # Resize image using light and fast Bilinear resampling
                resample_mode = getattr(Image, 'Resampling', Image).BILINEAR
                img = img.resize(VIDEO_SIZE, resample_mode)
                
                photo = ImageTk.PhotoImage(img)
                self.video_label.configure(image=photo)
                self.video_label.image = photo
                
                self.rendered_frames += 1
                
                # Update Statistics display
                total_expected = self.total_packets_received + self.lost_packets
                loss_rate = (self.lost_packets / total_expected * 100) if total_expected > 0 else 0.0
                
                self.packets_label.config(
                    text=f"Packets Rx: {self.total_packets_received}  |  Lost: {self.lost_packets}"
                )
                self.loss_rate_label.config(
                    text=f"Loss Rate: {loss_rate:.1f}%  |  Frames: {self.rendered_frames}"
                )
        except Exception as e:
            pass
        finally:
            # Run at approximately 20 FPS (50ms interval) or faster to process frames
            self.master.after(25, self.update_frame_loop)

    def on_close(self):
        if tkinter.messagebox.askokcancel("Quit", "Are you sure you want to quit?"):
            self.leave_stream()
            self.master.destroy()
            sys.exit(0)

if __name__ == "__main__":
    root = Tk()
    # Fixed geometry to prevent resizing issues
    root.geometry("680x480")
    root.resizable(False, False)
    
    app = MulticastClient(root)
    root.mainloop()