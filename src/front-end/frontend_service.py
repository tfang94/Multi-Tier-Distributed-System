from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import json
import re
import socket
import cgi
from urllib.parse import parse_qs
from optparse import OptionParser
import os

# Optional command line argument 
z = 1 # number of clients to wait before starting threads
d = 1 # indicates whether server is run on docker container, local machine, or elnux3 IP
c = 1 # in-memory cache flag

# in-memory cache
cache = {} 
invalidation_flag = {} # buy() and restock() invalidate, successful query resets

def push_cache(name, result):
    global cache
    global invalidation_flag
    cache[name] = result
    invalidation_flag[name] = False

# buy() and restock() invalidate cache to maintain cache consistency
def invalidate_item(name):
    global invalidation_flag
    if name is not None:
        invalidation_flag[name] = True

class httpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global z
        global d
        global c
        if z > 0:
            z -= 1
            while z > 0:
                pass
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        # GET /products/<product_name>
        route_regex = re.compile(r"^/products/(.+)$")
        path = self.path
        match = route_regex.match(path)
        host = '128.119.243.168'  # elnux3 IP
        if d == 1:
            host = os.getenv("CATALOG_IP", "catalog")
        if d == 2:
            host = '127.0.0.1'
        port = 12645  # catalog_service
        if match: # match exists for /products/<product name>
            name = match.group(1)
            if c == 1: # check cache
                lookup = cache.get(name)
                if lookup is not None:
                    if not invalidation_flag.get(name):
                        self.wfile.write(lookup.encode())
                        # print("cache hit")
                        return
            # contact catalog_service to call query method
            # print("cache miss")
            s = socket.socket()
            s.connect((host, port))
            msg = "Query " + name
            s.send(msg.encode())
            incoming = s.recv(1024).decode()  # results of call
            data = json.loads(incoming)
            # if query successful then push to cache
            if data.get("error") is None:
                print("successful query")
                push_cache(name, incoming)
            self.wfile.write(incoming.encode())  # write back to client
            s.close()
        
        # GET /orders/<order_number>
        route_regex = re.compile(r"^/orders/(.+)$")
        path = self.path
        match = route_regex.match(path)
        host = '128.119.243.168'  # elnux3 IP
        if d == 1:
            host = os.getenv("CATALOG_IP", "catalog")
        if d == 2:
            host = '127.0.0.1'
        port = 12745  # order_service
        if match:  # match exists for /orders/<order_number>
            order_id = match.group(1)
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
                if result >= 0: # succesful order
                    msg = str(result)
                    if c == 1:
                        invalidate_item(data.get("name")) # invalidate item in cache after successful buy()
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
    parser.add_option('-c', default=1, help='in-memory cache flag', action='store',
                      type='int', dest='c')    
    (options, args) = parser.parse_args()
    global z
    global d
    global c
    z = options.z
    d = options.d
    c = options.c
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
