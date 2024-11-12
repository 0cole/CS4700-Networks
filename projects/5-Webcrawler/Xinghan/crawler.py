#!/usr/bin/env python3

import argparse
import socket
import ssl
import urllib.parse
from html.parser import HTMLParser
import sys
import time

DEFAULT_SERVER = "fakebook.khoury.northeastern.edu"
DEFAULT_PORT = 443

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.flags = []
        self.links = []
        self.inside_flag = False

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            # Extract href attribute
            for attr in attrs:
                if attr[0] == 'href':
                    self.links.append(attr[1])
        elif tag == 'h3':
            for attr in attrs:
                if attr[0] == 'class' and 'secret_flag' in attr[1]:
                    self.inside_flag = True

    def handle_data(self, data):
        if self.inside_flag and 'FLAG:' in data:
            self.flags.append(data.strip())

    def handle_endtag(self, tag):
        if tag == 'h3' and self.inside_flag:
            self.inside_flag = False

class CSRFTokenParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.csrf_token = None
        self.next_value = ''

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'input':
            if attrs.get('name') == 'csrfmiddlewaretoken':
                self.csrf_token = attrs.get('value')
            elif attrs.get('name') == 'next':
                self.next_value = attrs.get('value', '')

class Crawler:
    def __init__(self, args):
        self.server = args.server
        self.port = args.port
        self.username = args.username
        self.password = args.password

        self.cookies = {}
        self.visited = set()
        self.to_visit = []
        self.flags = []

    def create_connection(self):
        context = ssl.create_default_context()
        # If you encounter SSL certificate issues, uncomment the following lines
        # context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        # context.check_hostname = False
        # context.verify_mode = ssl.CERT_NONE

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn = context.wrap_socket(sock, server_hostname=self.server)
        conn.connect((self.server, self.port))
        return conn

    def send_request(self, conn, request):
        conn.sendall(request.encode('utf-8'))

    def receive_response(self, conn):
        response = b''
        while True:
            data = conn.recv(4096)
            if not data:
                break
            response += data
        return response.decode('utf-8', errors='ignore')

    def get_csrf_token(self):
        path = '/accounts/login/?next=/fakebook/'
        conn = self.create_connection()
        request = f"GET {path} HTTP/1.1\r\n"
        request += f"Host: {self.server}\r\n"
        request += "User-Agent: CustomCrawler/1.0\r\n"
        request += "Accept: text/html\r\n"
        request += "Connection: close\r\n"
        request += f"Referer: https://{self.server}{path}\r\n"
        request += "Accept-Language: en-US,en;q=0.5\r\n\r\n"

        self.send_request(conn, request)
        response = self.receive_response(conn)
        conn.close()

        # Parse cookies from response headers
        headers, body = response.split('\r\n\r\n', 1)

        # Debugging: Print response headers
        print("Response Headers from GET request:", file=sys.stderr)
        print(headers, file=sys.stderr)

        self.parse_cookies(headers)

        # Debugging: Print cookies after parsing
        print(f"Cookies after GET request: {self.cookies}", file=sys.stderr)

        # Debugging: Print the HTML body of the login page
        print("Login page HTML:", file=sys.stderr)
        print(body, file=sys.stderr)

        # Extract CSRF token and next value from the body
        csrf_token, next_value = self.extract_csrf_token(body)

        # Update 'csrftoken' in cookies to match 'csrf_token'
        self.cookies['csrftoken'] = csrf_token

        return csrf_token, next_value


    def extract_csrf_token(self, html):
        parser = CSRFTokenParser()
        parser.feed(html)
        print(f"Extracted CSRF token: {parser.csrf_token}", file=sys.stderr)
        print(f"Extracted next value: {parser.next_value}", file=sys.stderr)
        return parser.csrf_token, parser.next_value

    def login(self):
        csrf_token, next_value = self.get_csrf_token()

        # Debugging: Print cookies before making the POST request
        print(f"Cookies before POST request: {self.cookies}", file=sys.stderr)

        path = '/accounts/login/'
        conn = self.create_connection()

        post_data = {
            'username': self.username,
            'password': self.password,
            'csrfmiddlewaretoken': csrf_token,
            'next': next_value
        }
        # URL-encode the POST data
        post_data_encoded = urllib.parse.urlencode(post_data)

        request = f"POST {path} HTTP/1.1\r\n"
        request += f"Host: {self.server}\r\n"
        request += "User-Agent: CustomCrawler/1.0\r\n"
        request += "Accept: text/html\r\n"
        request += "Connection: close\r\n"
        request += "Content-Type: application/x-www-form-urlencoded\r\n"
        request += f"Content-Length: {len(post_data_encoded)}\r\n"
        request += f"Referer: https://{self.server}/accounts/login/?next=/fakebook/\r\n"
        # Include cookies
        if self.cookies:
            cookie_header = 'Cookie: ' + '; '.join([f"{key}={value}" for key, value in self.cookies.items()])
            request += f"{cookie_header}\r\n"
        request += "\r\n"
        request += post_data_encoded

        # Debugging: Print the full request
        print("Full POST request:", file=sys.stderr)
        print(request, file=sys.stderr)

        self.send_request(conn, request)
        response = self.receive_response(conn)
        conn.close()

        # Parse cookies from response headers
        headers, body = response.split('\r\n\r\n', 1)
        self.parse_cookies(headers)

        # Debugging: Print response headers after POST request
        print("Response Headers from POST request:", file=sys.stderr)
        print(headers, file=sys.stderr)

        # Debugging: Print response body
        print("Response body from POST request:", file=sys.stderr)
        print(body, file=sys.stderr)

        # Get status code and location
        status_code = self.get_status_code(headers)
        new_location = self.get_location(headers)

        # Handle 302 redirect
        if status_code == 302 and new_location:
            # Assume login is successful if redirected to the 'next' page
            if new_location == next_value:
                print("Login successful.", file=sys.stderr)
                self.to_visit.append(new_location)
            else:
                print("Login redirected to unexpected location.", file=sys.stderr)
                sys.exit(1)
        else:
            print("Login failed.", file=sys.stderr)
            sys.exit(1)

    def parse_cookies(self, headers):
        # Collect all 'Set-Cookie' headers
        lines = headers.split('\r\n')
        for line in lines:
            if line.lower().startswith('set-cookie:'):
                cookie_line = line[len('Set-Cookie:'):].strip()
                # Extract the cookie name and value
                if ';' in cookie_line:
                    cookie_parts = cookie_line.split(';')
                    cookie_name_value = cookie_parts[0]
                    if '=' in cookie_name_value:
                        key, value = cookie_name_value.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        self.cookies[key] = value
                else:
                    if '=' in cookie_line:
                        key, value = cookie_line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        self.cookies[key] = value



    def crawl(self):
        while self.to_visit and len(self.flags) < 5:
            current_path = self.to_visit.pop(0)
            if current_path in self.visited:
                continue
            self.visited.add(current_path)
            self.visit_page(current_path)

    def visit_page(self, path):
        conn = self.create_connection()
        request = f"GET {path} HTTP/1.1\r\n"
        request += f"Host: {self.server}\r\n"
        request += "User-Agent: CustomCrawler/1.0\r\n"
        request += "Accept: text/html\r\n"
        request += "Connection: close\r\n"
        # Include cookies
        if self.cookies:
            cookie_header = 'Cookie: ' + '; '.join([f"{key}={value}" for key, value in self.cookies.items()])
            request += f"{cookie_header}\r\n"
        request += "\r\n"

        self.send_request(conn, request)
        response = self.receive_response(conn)
        conn.close()

        # Parse response
        headers, body = response.split('\r\n\r\n', 1)
        status_code = self.get_status_code(headers)

        # Debugging: Print status code and current path
        print(f"Visited {path} with status code {status_code}", file=sys.stderr)

        if status_code == 200:
            self.process_page(body)
        elif status_code == 302:
            # Handle redirect
            new_location = self.get_location(headers)
            if new_location and new_location not in self.visited:
                self.to_visit.append(new_location)
        elif status_code == 403 or status_code == 404:
            # Do not retry; ignore this URL
            pass
        elif status_code == 503:
            # Retry after delay
            time.sleep(1)
            self.to_visit.append(path)
        else:
            # Handle other status codes as needed
            pass

    def get_status_code(self, headers):
        status_line = headers.split('\r\n')[0]
        parts = status_line.split(' ')
        if len(parts) >= 2:
            return int(parts[1])
        return None

    def get_location(self, headers):
        for line in headers.split('\r\n'):
            if line.lower().startswith('location:'):
                location = line[len('Location:'):].strip()
                # Handle potential case differences in 'Location'
                location = line[line.find(':')+1:].strip()
                parsed_url = urllib.parse.urlparse(location)
                # Handle absolute and relative URLs
                if parsed_url.netloc == '':
                    return parsed_url.path
                elif parsed_url.netloc == self.server:
                    return parsed_url.path
                else:
                    # Ignore redirects to other domains
                    return None
        return None

    def process_page(self, html):
        parser = MyHTMLParser()
        parser.feed(html)
        # Add new flags
        for flag in parser.flags:
            if flag not in self.flags:
                self.flags.append(flag)
                print(flag)
                if len(self.flags) == 5:
                    sys.exit(0)
        # Add new links to the frontier
        for link in parser.links:
            full_url = urllib.parse.urljoin(f'https://{self.server}', link)
            parsed_url = urllib.parse.urlparse(full_url)
            if parsed_url.netloc == self.server:
                path = parsed_url.path
                if path not in self.visited and path not in self.to_visit:
                    self.to_visit.append(path)

    def run(self):
        self.login()
        self.crawl()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='crawl Fakebook')
    parser.add_argument('-s', dest="server", type=str, default=DEFAULT_SERVER, help="The server to crawl")
    parser.add_argument('-p', dest="port", type=int, default=DEFAULT_PORT, help="The port to use")
    parser.add_argument('username', type=str, help="The username to use")
    parser.add_argument('password', type=str, help="The password to use")
    args = parser.parse_args()
    crawler = Crawler(args)
    crawler.run()
