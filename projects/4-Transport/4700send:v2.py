#!/usr/bin/env -S python3 -u

import argparse, socket, time, json, select, struct, sys, math

DATA_SIZE = 1375
import zlib

def calculate_checksum(data):
    return zlib.crc32(data.encode('utf-8')) & 0xffffffff

def verify_checksum(data, received_checksum):
    calculated_checksum = calculate_checksum(data)
    return calculated_checksum == received_checksum


class Sender:
    def __init__(self, host, port):
        self.seq_num = 0
        self.send_base = 0
        self.packets = {}  # Store sent packets and their send times
        self.estimated_rtt = 1.0  # Initial RTT estimate
        self.timeout_interval = 1.0  # Initial timeout

        # Congestion control variables
        self.cwnd = 1.0           # Initial congestion window size
        self.dwnd = 0.0           # Initial delay window size
        self.adv_wnd = float('inf')  # Receiver's advertised window (set to a large value)
        self.ssthresh = 64.0      # Slow start threshold
        self.prev_sample_rtt = None  # Previous RTT sample

        self.host = host
        self.port = int(port)
        self.log(f"Sender starting up using port {self.port}")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', 0))

        self.remote_host = None
        self.remote_port = None

    def log(self, message):
        sys.stderr.write(message + "\n")
        sys.stderr.flush()

    def send(self, message):
        # self.log(f"Sending message '{json.dumps(message)}'")  # Uncomment to log sent messages
        self.socket.sendto(json.dumps(message).encode("utf-8"), (self.host, self.port))

    def recv(self, socket):
        data, addr = socket.recvfrom(65535)
        if addr[0] != self.host or addr[1] != self.port:
            self.log("Received packet from unknown source; ignoring")
            return None
        else:
            message = json.loads(data.decode("utf-8"))
            # self.log(f"Received message {message}")  # Uncomment to log received messages
            return message

    def handle_ack(self, ack_seq_num):
        self.log(f"Received ACK for seq {ack_seq_num}")
        if ack_seq_num in self.packets:
            # Update RTT estimation
            sample_rtt = time.time() - self.packets[ack_seq_num]['send_time']
            self.estimated_rtt = 0.875 * self.estimated_rtt + 0.125 * sample_rtt
            self.timeout_interval = self.estimated_rtt * 2

            # Adjust cwnd (Congestion Window) using AIMD
            if self.cwnd < self.ssthresh:
                # Slow start phase
                self.cwnd += 1.0
            else:
                # Congestion avoidance phase
                self.cwnd += 1.0 / self.cwnd

            # Adjust dwnd (Delay Window)
            if self.prev_sample_rtt is not None:
                rtt_change = sample_rtt - self.prev_sample_rtt
                rate_of_change = rtt_change / self.prev_sample_rtt
                if rtt_change < 0:
                    # RTT decreased: increase dwnd proportionally
                    self.dwnd += -rate_of_change
                else:
                    # RTT increased: decrease dwnd proportionally
                    self.dwnd -= rate_of_change
                    self.dwnd = max(self.dwnd, 0.0)  # Ensure dwnd >= 0
            self.prev_sample_rtt = sample_rtt

            # Remove acknowledged packet
            del self.packets[ack_seq_num]
            if ack_seq_num == self.send_base:
                # Slide the window forward
                while self.send_base not in self.packets and self.send_base < self.seq_num:
                    self.send_base += 1
        else:
            self.log(f"Received duplicate or out-of-window ACK for seq {ack_seq_num}")

        # Update window size after adjusting cwnd and dwnd
        self.window_size = max(1, int(min(self.cwnd + self.dwnd, self.adv_wnd)))
        self.log(f"Updated window size to {self.window_size}")

    def check_timeouts(self):
        current_time = time.time()
        timeout_occurred = False
        for seq_num, info in list(self.packets.items()):
            if current_time - info["send_time"] > self.timeout_interval:
                # Timeout occurred
                timeout_occurred = True
                self.log(f"Timeout occurred for seq {seq_num}, retransmitting packet")
                # Multiplicative decrease
                self.ssthresh = max(self.cwnd / 2, 1.0)
                self.cwnd = 1.0  # Reset cwnd to 1
                # Reset dwnd
                self.dwnd = 0.0
                # Retransmit packet
                self.send(info["packet"])
                # Update send time
                self.packets[seq_num]["send_time"] = current_time
                break  # Handle one timeout at a time

        if timeout_occurred:
            # Update window size after adjusting cwnd and dwnd
            self.window_size = max(1, int(min(self.cwnd + self.dwnd, self.adv_wnd)))
            self.log(f"Adjusted cwnd to {self.cwnd}, window size to {self.window_size}")

    def run(self):
        data_finished = False  # Flag to indicate if all data has been read
        while True:
            # Update window size at the beginning of each loop
            self.window_size = max(1, int(min(self.cwnd + self.dwnd, self.adv_wnd)))
            # Send new packets if window is not full and data is available
            while self.seq_num < self.send_base + self.window_size and not data_finished:
                data = sys.stdin.read(DATA_SIZE)
                if not data:
                    data_finished = True  # No more data to send
                    break
                # Create packet with sequence number and checksum
                packet = {
                    "type": "msg",
                    "data": data,
                    "seq": self.seq_num,
                    "checksum": calculate_checksum(data),
                }
                self.send(packet)
                self.packets[self.seq_num] = {
                    "packet": packet,
                    "send_time": time.time(),
                }
                self.seq_num += 1

            # Determine the timeout for select
            if self.packets:
                earliest_send_time = min(info['send_time'] for info in self.packets.values())
                time_since_earliest = time.time() - earliest_send_time
                timeout = max(self.timeout_interval - time_since_earliest, 0)
            else:
                timeout = None  # No unacknowledged packets

            # Use select to wait for incoming ACKs or timeout
            readable, _, _ = select.select([self.socket], [], [], timeout)

            if readable:
                for conn in readable:
                    if conn == self.socket:
                        ack_packet = self.recv(conn)
                        if ack_packet and ack_packet.get('type') == 'ack':
                            self.handle_ack(ack_packet['seq'])
            else:
                # Timeout occurred; adjust cwnd and retransmit packets
                self.check_timeouts()

            # Check if all data has been sent and acknowledged
            if data_finished and not self.packets:
                self.log("All data sent and acknowledged")
                break
            else:
                self.log(f"Unacknowledged packets: {list(self.packets.keys())}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='send data')
    parser.add_argument('host', type=str, help="Remote host to connect to")
    parser.add_argument('port', type=int, help="UDP port number to connect to")
    args = parser.parse_args()
    sender = Sender(args.host, args.port)
    sender.run()
