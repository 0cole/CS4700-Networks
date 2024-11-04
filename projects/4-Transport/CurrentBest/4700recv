#!/usr/bin/env -S python3 -u

import argparse, socket, time, json, select, struct, sys, math
import zlib

def calculate_checksum(data):
    return zlib.crc32(data.encode('utf-8')) & 0xffffffff

def verify_checksum(data, received_checksum):
    calculated_checksum = calculate_checksum(data)
    return calculated_checksum == received_checksum

class Receiver:
    def __init__(self):
        self.expected_seq_num = 0
        self.buffer = {}
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('0.0.0.0', 0))
        self.port = self.socket.getsockname()[1]
        self.log("Bound to port %d" % self.port)

        self.remote_host = None
        self.remote_port = None

    def send(self, message):
        if self.remote_host is not None and self.remote_port is not None:
            self.log(f"Sending ACK for seq {message['seq']} with SACK {message.get('sack', [])}")
            self.socket.sendto(json.dumps(message).encode("utf-8"), (self.remote_host, self.remote_port))
        else:
            self.log("Remote host and port not set; cannot send ACK")

    def recv(self, socket):
        data, addr = socket.recvfrom(65535)

        # Set the remote host and port if not already set
        if self.remote_host is None:
            self.remote_host = addr[0]
            self.remote_port = addr[1]
            self.log(f"Set remote host to {self.remote_host}, port to {self.remote_port}")

        message = json.loads(data.decode("utf-8"))
        return message

    def log(self, message):
        sys.stderr.write(message + "\n")
        sys.stderr.flush()

    def run(self):
        while True:
            # Use select to wait for incoming packets
            readable, _, _ = select.select([self.socket], [], [], None)
            for conn in readable:
                msg = self.recv(conn)
                if msg:
                    # Verify checksum
                    if not verify_checksum(msg['data'], msg['checksum']):
                        self.log(f"Checksum mismatch for seq {msg['seq']}; discarding packet")
                        # Do not send ACK for corrupted packet
                        continue  # Move to the next packet

                    seq_num = msg['seq']

                    if seq_num == self.expected_seq_num:
                        # Deliver data to stdout
                        print(msg['data'], end='', flush=True)
                        self.expected_seq_num += 1
                        # Check if we have buffered packets to deliver
                        while self.expected_seq_num in self.buffer:
                            buffered_msg = self.buffer.pop(self.expected_seq_num)
                            print(buffered_msg['data'], end='', flush=True)
                            self.expected_seq_num += 1
                        self.log(f"Received expected packet seq {seq_num}")
                    elif seq_num > self.expected_seq_num:
                        # Buffer out-of-order packet
                        self.buffer[seq_num] = msg
                        self.log(f"Buffered out-of-order packet seq {seq_num}")
                    else:
                        # Duplicate packet; already received and processed
                        self.log(f"Received duplicate packet seq {seq_num}; discarding")

                    # Prepare the SACK information
                    sack_list = sorted(self.buffer.keys())
                    ack_packet = {
                        "type": "ack",
                        "seq": self.expected_seq_num,
                        "sack": sack_list,
                    }
                    self.send(ack_packet)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='receive data')
    args = parser.parse_args()
    receiver = Receiver()
    receiver.run()
