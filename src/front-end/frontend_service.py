from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
import re
import socket
import cgi
from urllib.parse import parse_qs
from optparse import OptionParser
import os

# Optional command line argument z specifies number of clients to wait before starting threads
# and d indicates whether server is run on docker container or elnux3 IP
z = 1
d = 1


class httpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global z
        global d
        if z > 0:
            z -= 1
            while z > 0:
                pass
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        # GET /products/<product_name>
        # Check if match exists for /products/<product name>
        route_regex = re.compile(r"^/products/(.+)$")
        path = self.path
        match = route_regex.match(path)
        if match:  # contact catalog_service to call Query() method
            name = match.group(1)
            host = '128.119.243.168'  # elnux3 IP
            if d == 1:
                host = os.getenv("CATALOG_IP", "catalog")
            if d == 2:
                host = '127.0.0.1'
            port = 12645  # port number catalog_service is running on
            s = socket.socket()
            s.connect((host, port))
            msg = "Query " + name  # call query method
            s.send(msg.encode())
            incoming = s.recv(1024)  # results of call
            self.wfile.write(incoming)  # write back to client
            s.close()
        
        # GET /orders/<order_number>
        route_regex = re.compile(r"^/orders/(.+)$")
        path = self.path
        match = route_regex.match(path)
        if match:  # contact catalog_service to call Query() method
            order_id = match.group(1)
            host = '128.119.243.168'  # elnux3 IP
            if d == 1:
                host = os.getenv("CATALOG_IP", "catalog")
            if d == 2:
                host = '127.0.0.1'
            port = 12745  # port number order_service is running on
            s = socket.socket()
            s.connect((host, port))
            msg = "getOrder " + order_id  # call query method
            s.send(msg.encode())
            incoming = s.recv(1024)  # results of call
            self.wfile.write(incoming)  # write back to client
            s.close()

    def do_POST(self):
        global d
        # Parse POST form
        ctype, pdict = cgi.parse_header(self.headers['content-type'])
        if ctype == 'multipart/form-data':
            postvars = cgi.parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            length = int(self.headers['content-length'])
            postvars = parse_qs(
                self.rfile.read(length),
                keep_blank_values=1)
        else:
            postvars = {}
        data = {}
        for key, value in postvars.items():  # clean POST form into dictionary of strings
            data[key.decode()] = value[0].decode()

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        if self.path == "/orders":
            host = '128.119.243.168'  # elnux3 IP
            if d == 1:
                host = os.getenv("ORDER_IP", "order")
            if d == 2:
                host = '127.0.0.1'
            port = 12745  # port number order_service is running on
            s = socket.socket()
            s.connect((host, port))
            msg = "processOrder " + json.dumps(data)
            s.send(msg.encode())
            incoming = s.recv(1024)  # results of call
            msg = None
            try:
                result = int(incoming.decode())
                if result >= 0:
                    msg = str(result)
                if result == -1:
                    msg = json.dumps(
                        {"error": {"code": 404, "message": "product not found"}})
                if result == -2:
                    msg = json.dumps(
                        {"error": {"code": 404, "message": "product out of stock"}})
            except:
                msg = incoming.decode()
            self.wfile.write(msg.encode())  # write back to client
            s.close()
        return


def main():
    # Optional command line argumentz (default 1) specifies number
    # of clients to wait before starting threads
    parser = OptionParser()
    parser.add_option('-z', default=1, help='Parameter for probability of sending order request', action='store',
                      type='int', dest='z')
    parser.add_option('-d', default=1, help='Running on docker', action='store',
                      type='int', dest='d')
    (options, args) = parser.parse_args()
    global z
    global d
    z = options.z
    d = options.d
    host = '128.119.243.168'  # elnux3 IP
    if d == 1:
        host = socket.gethostbyname(socket.gethostname())
    if d == 2:
        host = '127.0.0.1'
    PORT = 8001
    server = ThreadingHTTPServer((host, PORT), httpHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
