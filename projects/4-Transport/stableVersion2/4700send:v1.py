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
        self.window_size = 6  # window size
        self.packets = {}  # each package contain send times
        self.estimated_rtt = 1.0  # Initial RTT estimate
        self.timeout_interval = 1.0  # Initial timeout

        self.host = host
        self.port = int(port)
        self.log("Sender starting up using port %s" % self.port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', 0))
        self.waiting = False

        self.remote_host = None
        self.remote_port = None

    def log(self, message):
        sys.stderr.write(message + "\n")
        sys.stderr.flush()

    def send(self, message):
        self.log(f"Sending packet with seq {message['seq']}")
        self.socket.sendto(json.dumps(message).encode("utf-8"), (self.host, self.port))

    def recv(self, socket):
        data, addr = socket.recvfrom(65535)
        if addr[0] != self.host or addr[1] != self.port:
            self.log("Received packet from unknown source; ignoring")
            return None
        else:
            message = json.loads(data.decode("utf-8"))
            # self.log(f"Received message {message}") # print message received
            return message

    def handle_ack(self, ack_seq_num):
        self.log(f"Received ACK for seq {ack_seq_num}")
        if ack_seq_num > self.send_base:
            # Update RTT estimation using the last acknowledged packet
            last_acked_seq_num = ack_seq_num - 1
            if last_acked_seq_num in self.packets:
                sample_rtt = time.time() - self.packets[last_acked_seq_num]['send_time']
                self.estimated_rtt = 0.875 * self.estimated_rtt + 0.125 * sample_rtt
                self.timeout_interval = self.estimated_rtt * 2

            # Remove all acknowledged packets from self.packets
            for seq_num in range(self.send_base, ack_seq_num):
                if seq_num in self.packets:
                    del self.packets[seq_num]

            # Slide the window forward
            self.send_base = ack_seq_num
        else:
            self.log(f"Received duplicate or out-of-window ACK for seq {ack_seq_num}")


    def run(self):
        data_finished = False  # Flag to indicate if all data has been read
        while True:
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
                # Timeout occurred; retransmit all unacknowledged packets
                self.log("Timeout occurred, retransmitting packets")
                for seq_num in sorted(self.packets.keys()):
                    packet_info = self.packets[seq_num]
                    self.send(packet_info['packet'])
                    packet_info['send_time'] = time.time()  # Update send time

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
