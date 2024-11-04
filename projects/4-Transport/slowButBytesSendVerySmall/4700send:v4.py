#!/usr/bin/env -S python3 -u

import argparse, socket, time, json, select, struct, sys, math
import zlib

DATA_SIZE = 1375

def calculate_checksum(data):
    return zlib.crc32(data.encode('utf-8')) & 0xffffffff

def verify_checksum(data, received_checksum):
    calculated_checksum = calculate_checksum(data)
    return calculated_checksum == received_checksum


class Sender:
    def __init__(self, host, port):
        self.seq_num = 0
        self.send_base = 0
        self.cwnd = 1  # Congestion window size
        self.ssthresh = 10  # Slow start threshold
        self.dup_ack_count = 0  # Duplicate ACK counter
        self.last_ack_num = -1  # Last acknowledged sequence number

        self.packets = {}  # Dictionary to store sent packets with their send times
        self.estimated_rtt = 0.5  # Initial RTT estimate
        self.timeout_interval = 1.0  # Initial timeout interval

        self.host = host
        self.port = int(port)
        self.log(f"Sender starting up using port {self.port}")
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', 0))

        self.remote_host = None
        self.remote_port = None

        self.previous_sack_set = set()  # Set to keep track of previously SACKed sequence numbers

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
            return message  # Return the entire ACK packet

    def handle_ack(self, ack_packet):
        ack_seq_num = ack_packet['seq']
        sack_list = ack_packet.get('sack', [])
        self.log(f"Received ACK for seq {ack_seq_num} with SACK {sack_list}")
        sack_set = set(sack_list)

        # Combine cumulative ACK and SACKed packets
        acked_seqs = set(range(self.send_base, ack_seq_num)) | sack_set

        # Remove all acknowledged packets from self.packets
        for seq_num in acked_seqs:
            if seq_num in self.packets:
                del self.packets[seq_num]

        # Update send_base
        if ack_seq_num > self.send_base:
            # New cumulative ACK received
            self.last_ack_num = ack_seq_num
            self.dup_ack_count = 0

            # Update RTT estimation if the packet was not retransmitted
            last_acked_seq_num = ack_seq_num - 1
            packet_info = self.packets.get(last_acked_seq_num)
            if packet_info and not packet_info.get('retransmitted', False):
                sample_rtt = time.time() - packet_info['send_time']
                # Update Estimated RTT and RTT Deviation
                self.estimated_rtt = 0.875 * self.estimated_rtt + 0.125 * sample_rtt
                # Update Timeout Interval
                self.timeout_interval = self.estimated_rtt * 2
                self.log(f"Upddate timeout intercal to {self.timeout_interval}")

            self.send_base = ack_seq_num

            # Update congestion window
            if self.cwnd < self.ssthresh:
                # Slow Start phase
                self.cwnd += 1
                self.log(f"Slow Start: Increased cwnd to {self.cwnd}")
            else:
                # Congestion Avoidance phase
                increment = 1 / self.cwnd
                self.cwnd += increment
                self.log(f"Congestion Avoidance: Increased cwnd to {self.cwnd}")

            # Reset previous SACK set
            self.previous_sack_set = set()

        elif ack_seq_num == self.last_ack_num:
            # Duplicate ACK received
            if sack_list:
                # Check for new SACKed packets
                new_sacks = sack_set - self.previous_sack_set
                if new_sacks:
                    # New packets have been SACKed; reset dup_ack_count
                    self.dup_ack_count = 0
                else:
                    self.dup_ack_count += 1
                self.previous_sack_set = sack_set
            else:
                self.dup_ack_count += 1

            self.log(f"Received duplicate ACK {self.dup_ack_count} for seq {ack_seq_num}")

            if self.dup_ack_count >= 3:
                # Triple duplicate ACKs detected; perform fast retransmit
                self.log("Triple duplicate ACKs detected, performing fast retransmit")
                old_cwnd = self.cwnd
                self.ssthresh = max(old_cwnd / 2, 2)
                self.cwnd = self.ssthresh + 3  # Fast recovery
                self.log(f"Updated ssthresh to {self.ssthresh}, cwnd to {self.cwnd}")

                # Retransmit the missing packet
                missing_seqs = set(range(self.send_base, self.seq_num)) - acked_seqs
                if missing_seqs:
                    seq_num = min(missing_seqs)
                    if seq_num in self.packets:
                        packet_info = self.packets[seq_num]
                        self.send(packet_info['packet'])
                        packet_info['send_time'] = time.time()
                        packet_info['retransmitted'] = True  # Mark as retransmitted
        else:
            # Out-of-order or old ACK received
            self.log(f"Received out-of-order or old ACK for seq {ack_seq_num}")

    def run(self):
        data_finished = False  # Indicates if all data has been read
        while True:
            # Send new packets if window is not full and data is available
            while self.seq_num < self.send_base + int(self.cwnd) and not data_finished:
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
                    "retransmitted": False,  # Initial transmission
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
                            self.handle_ack(ack_packet)
            else:
                # Timeout occurred; retransmit unacknowledged packets
                self.log("Timeout occurred, retransmitting unacknowledged packets")
                old_cwnd = self.cwnd
                self.ssthresh = max(old_cwnd / 2, 2)
                self.cwnd = 1
                self.log(f"Updated ssthresh to {self.ssthresh}, cwnd to {self.cwnd}")
                for seq_num in sorted(self.packets.keys()):
                    packet_info = self.packets[seq_num]
                    self.send(packet_info['packet'])
                    packet_info['send_time'] = time.time()
                    packet_info['retransmitted'] = True  # Mark as retransmitted

            # Check if all data has been sent and acknowledged
            if data_finished and not self.packets:
                self.log("All data sent and acknowledged")
                break
            else:
                if self.packets:
                    unacked_seqs = sorted(self.packets.keys())
                    self.log(f"Unacknowledged packets: {unacked_seqs}")
                else:
                    self.log("No unacknowledged packets")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='send data')
    parser.add_argument('host', type=str, help="Remote host to connect to")
    parser.add_argument('port', type=int, help="UDP port number to connect to")
    args = parser.parse_args()
    sender = Sender(args.host, args.port)
    sender.run()
