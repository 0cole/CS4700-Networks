#!/usr/bin/env -S python3 -u

import argparse, socket, time, json, select, struct, sys, math
from dnslib import DNSRecord, DNSHeader, RR, QTYPE, RCODE, A, CNAME, MX, NS, TXT, SOA, DNSQuestion
import threading

class Server:
    def __init__(self, root_ip, zone_file, port):
        self.root_ip = root_ip
        self.zone_file = zone_file
        self.records = {}   # { (name, qtype): [RR, ...] } 
        self.authoritative_domain = None

        self.parse_zone_file()
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("0.0.0.0", port))
        self.port = self.socket.getsockname()[1]

        self.log("Bound to port %d" % self.port)

    def log(self, message):
        sys.stderr.write(message + "\n")
        sys.stderr.flush()

    def send(self, addr, message):
        self.log("Sending message:\n%s" % message)
        self.socket.sendto(message.pack(), addr)

    def parse_zone_file(self):
        with open(self.zone_file, "r") as f:
            zone_data = f.read()

        rrs = RR.fromZone(zone_data)

        # Find SOA to determine authoritative domain
        soa_record = None
        for rr in rrs:
            if rr.rtype == QTYPE.SOA:
                soa_record = rr
                break

        if not soa_record:
            self.log("No SOA record found in zone file. Cannot determine authoritative domain.")
            sys.exit(1)

        self.authoritative_domain = str(soa_record.rname)
        if not self.authoritative_domain.endswith('.'):
            self.authoritative_domain += '.'

        for rr in rrs:
            name = str(rr.rname)
            qtype = rr.rtype
            key = (name.lower(), qtype)
            if key not in self.records:
                self.records[key] = []
            self.records[key].append(rr)

        self.log("Loaded zone for domain: %s" % self.authoritative_domain)

    def is_under_authoritative_domain(self, qname):
        qname = qname.lower()
        return qname.endswith(self.authoritative_domain)

    def lookup_records(self, qname, qtype):
        qname = qname.lower()
        key = (qname, qtype)
        return self.records.get(key, [])

    def handle_authoritative_query(self, request):
        q = request.q
        qname = str(q.qname)
        qtype = q.qtype

        answers = self.lookup_records(qname, qtype)

        if not answers:
            # Check for CNAME if no direct answers
            cname_records = self.lookup_records(qname, QTYPE.CNAME)
            if cname_records:
                answers.extend(cname_records)
                # If the client wanted A and we have a CNAME, try to add A record of the target if in-domain
                if qtype == QTYPE.A:
                    target = str(cname_records[0].rdata.label)
                    if self.is_under_authoritative_domain(target):
                        a_rrs = self.lookup_records(target, QTYPE.A)
                        answers.extend(a_rrs)

        additional = []
        if qtype == QTYPE.NS and answers:
            for rr in answers:
                if rr.rtype == QTYPE.NS:
                    ns_name = str(rr.rdata.label)
                    a_rrs = self.lookup_records(ns_name, QTYPE.A)
                    additional.extend(a_rrs)

        if not answers:
            if self.is_under_authoritative_domain(qname):
                # NXDOMAIN
                response = request.reply()
                response.header.rcode = RCODE.NXDOMAIN
                response.header.aa = 1
                return response
            else:
                # Outside authoritative domain, no recursion means SERVFAIL
                response = request.reply()
                response.header.rcode = RCODE.SERVFAIL
                return response

        response = request.reply()
        response.header.aa = 1
        for ans in answers:
            response.add_answer(ans)
        for addl in additional:
            response.add_ar(addl)
        return response

    def handle_request(self, request, addr):
        orig_id = request.header.id
        # Multiple questions => SERVFAIL
        if len(request.questions) != 1:
            response = request.reply()
            response.header.rcode = RCODE.SERVFAIL
            response.header.id = orig_id
            self.send(addr, response)
            return

        q = request.q
        qname = str(q.qname)
        qtype = q.qtype

        # If in our authoritative domain, answer directly
        if self.is_under_authoritative_domain(qname):
            response = self.handle_authoritative_query(request)
            # Ensure same id
            response.header.id = orig_id
            self.send(addr, response)
            return
        else:
            # Not in our domain
            # Check RD flag
            if request.header.rd == 1:
                # Perform recursion in a separate thread so we can handle other requests
                threading.Thread(target=self.handle_recursive_request, args=(qname, qtype, orig_id, addr)).start()
                return
            else:
                # No recursion requested, return SERVFAIL
                response = request.reply()
                response.header.id = orig_id
                response.header.rcode = RCODE.SERVFAIL
                self.send(addr, response)
                return

    def handle_recursive_request(self, qname, qtype, orig_id, addr):
        response = self.recursive_resolve(qname, qtype, orig_id)
        # Set RA = 1 since we performed recursion
        response.header.ra = 1
        response.header.id = orig_id
        self.send(addr, response)

    def send_udp_query(self, qname, qtype, server_ip, timeout=2):
        query = DNSRecord.question(qname, QTYPE[qtype])
        self.log("Sending recursive query for %s (%s) to %s" % (qname, QTYPE[qtype], server_ip))
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        try:
            s.sendto(query.pack(), (server_ip, 60053))
            data, _ = s.recvfrom(65535)
            response = DNSRecord.parse(data)
            return response
        except socket.timeout:
            self.log("Timeout waiting for response from %s" % server_ip)
            return None
        except Exception as e:
            self.log("Error querying %s: %s" % (server_ip, e))
            return None
        finally:
            s.close()

    def filter_bailiwick(self, rrset, bailiwick_domain):
        # Remove any records that are not under the current bailiwick
        filtered = []
        for rr in rrset:
            if str(rr.rname).lower().endswith(bailiwick_domain):
                filtered.append(rr)
        return filtered

    def recursive_resolve(self, qname, qtype, orig_id):
        current_server = self.root_ip
        original_qname = qname
        visited = set()

        # Start at the root bailiwick
        current_bailiwick = "."

        while True:
            if (current_server, qname, qtype) in visited:
                return self.make_error_response(original_qname, qtype, RCODE.SERVFAIL, orig_id)
            visited.add((current_server, qname, qtype))

            response = self.send_udp_query(qname, qtype, current_server)
            if response is None:
                return self.make_error_response(original_qname, qtype, RCODE.SERVFAIL, orig_id)

            # Filter all sections for bailiwick (including answer section)
            response.rr = self.filter_bailiwick(response.rr, current_bailiwick)
            response.auth = self.filter_bailiwick(response.auth, current_bailiwick)
            response.ar = self.filter_bailiwick(response.ar, current_bailiwick)

            if response.header.rcode == RCODE.NOERROR:
                if len(response.rr) > 0:
                    # Got answers, return them
                    final_response = self.follow_cname_if_needed(response, current_server, orig_id)
                    return final_response

                # No answers, maybe a delegation?
                ns_records = [r for r in response.auth if r.rtype == QTYPE.NS]
                if ns_records:
                    if qtype == QTYPE.NS:
                        # Return NOERROR with NS records
                        final = DNSRecord(
                            DNSHeader(id=orig_id, qr=1, ra=1, aa=0, rcode=RCODE.NOERROR),
                            q=DNSQuestion(original_qname, qtype)
                        )
                        for ns_rr in ns_records:
                            final.add_auth(ns_rr)
                        for ar_rr in response.ar:
                            if ar_rr.rtype == QTYPE.A and any(str(ns_rr.rdata.label) == str(ar_rr.rname) for ns_rr in ns_records):
                                final.add_ar(ar_rr)
                        return final

                    # Follow delegation
                    ns_name = str(ns_records[0].rdata.label)
                    ns_ip = self.find_nameserver_ip(ns_name, response)
                    if not ns_ip:
                        ns_response = self.recursive_resolve(ns_name, QTYPE.A, orig_id)
                        if ns_response.header.rcode == RCODE.NOERROR and ns_response.rr:
                            for rr in ns_response.rr:
                                if rr.rtype == QTYPE.A and str(rr.rname) == ns_name:
                                    ns_ip = str(rr.rdata)
                                    break
                    if ns_ip:
                        # Update bailiwick to the NS owner's domain
                        new_bailiwick = str(ns_records[0].rname)
                        if not new_bailiwick.endswith('.'):
                            new_bailiwick += '.'
                        current_bailiwick = new_bailiwick.lower()

                        current_server = ns_ip
                        continue
                    else:
                        # Can't find NS IP, return SERVFAIL
                        return self.make_error_response(original_qname, qtype, RCODE.SERVFAIL, orig_id)
                else:
                    # No answers, no NS, check for SOA => NXDOMAIN
                    soa_records = [r for r in response.auth if r.rtype == QTYPE.SOA]
                    if soa_records:
                        return self.make_error_response(original_qname, qtype, RCODE.NXDOMAIN, orig_id)
                    else:
                        # No data, no NXDOMAIN => NOERROR empty
                        final = DNSRecord(
                            DNSHeader(id=orig_id, qr=1, ra=1, aa=0, rcode=RCODE.NOERROR),
                            q=DNSQuestion(original_qname, qtype)
                        )
                        return final

            elif response.header.rcode == RCODE.NXDOMAIN:
                return self.make_error_response(original_qname, qtype, RCODE.NXDOMAIN, orig_id)
            else:
                # Other errors => SERVFAIL
                return self.make_error_response(original_qname, qtype, RCODE.SERVFAIL, orig_id)

    def follow_cname_if_needed(self, response, current_server, orig_id):
        qname = str(response.q.qname)
        qtype = response.q.qtype

        desired_answers = [r for r in response.rr if r.rtype == qtype]
        if desired_answers:
            final = DNSRecord(DNSHeader(id=orig_id, qr=1, ra=0, aa=0, rcode=RCODE.NOERROR), q=response.q)
            for r in response.rr:
                final.add_answer(r)
            for r in response.auth:
                final.add_auth(r)
            for r in response.ar:
                final.add_ar(r)
            return final

        cname_answers = [r for r in response.rr if r.rtype == QTYPE.CNAME]
        if cname_answers:
            cname_target = str(cname_answers[0].rdata.label)
            cname_resp = self.recursive_resolve(cname_target, qtype, orig_id)
            if cname_resp.header.rcode == RCODE.NOERROR:
                final = DNSRecord(DNSHeader(id=orig_id, qr=1, ra=0, aa=0, rcode=RCODE.NOERROR), q=response.q)
                for crr in cname_answers:
                    final.add_answer(crr)
                for rr in cname_resp.rr:
                    final.add_answer(rr)
                for rr in cname_resp.auth:
                    final.add_auth(rr)
                for rr in cname_resp.ar:
                    final.add_ar(rr)
                return final
            else:
                return cname_resp

        # No desired answers, no CNAME => return NOERROR empty
        final = DNSRecord(
            DNSHeader(id=orig_id, qr=1, ra=0, aa=0, rcode=RCODE.NOERROR),
            q=response.q
        )
        return final

    def find_nameserver_ip(self, ns_name, response):
        for rr in response.ar:
            if rr.rtype == QTYPE.A and str(rr.rname) == ns_name:
                return str(rr.rdata)
        return None

    def make_error_response(self, qname, qtype, rcode, orig_id):
        hdr = DNSHeader(id=orig_id, qr=1, aa=0, ra=0, rcode=rcode)
        question = DNSQuestion(qname, qtype)
        response = DNSRecord(hdr, q=question)
        return response

    def recv(self, socket):
        data, addr = socket.recvfrom(65535)
        try:
            request = DNSRecord.parse(data)
        except Exception as e:
            self.log("Failed to parse DNS request: %s" % str(e))
            # Return FORMERR
            req_id = struct.unpack("!H", data[:2])[0]
            header = DNSHeader(id=req_id, qr=1, ra=0, rcode=RCODE.FORMERR)
            response = DNSRecord(header)
            self.send(addr, response)
            return

        self.log("Received message:\n%s" % request)
        
        self.handle_request(request, addr)

    def run(self):
        while True:
            socks = select.select([self.socket], [], [], 0.1)[0]
            for conn in socks:
                self.recv(conn)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='DNS Server')
    parser.add_argument('root_ip', type=str, help="The IP address of the root server")
    parser.add_argument('zone', type=str, help="The zone file for this server")
    parser.add_argument('--port', type=int, help="The port this server should bind to", default=0)
    args = parser.parse_args()

    sender = Server(args.root_ip, args.zone, args.port)
    sender.run()
