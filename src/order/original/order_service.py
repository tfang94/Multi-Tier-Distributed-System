import socket
from readerwriterlock import rwlock
from concurrent.futures import ThreadPoolExecutor
import json
from optparse import OptionParser
import os
import re

a = rwlock.RWLockFairD()
# Optional command line argument d indicates whether server is run on docker container or elnux3 IP
d = 1


def processOrder(order):
    # Input: dictionary
    # Output: order ID
    # Polls catalog_service to see if in stock.  If so, tell catalog_service to decrement toy quantity.
    # Then create new order entry in order.txt
    global a
    global d
    host = '128.119.243.168'  # elnux3 IP
    if d == 1:
        host = os.getenv("CATALOG_IP", "catalog")
    if d == 2:
        host = '127.0.0.1'
    port = 12645
    s = socket.socket()
    s.connect((host, port))  # Connect to catalog service
    name = order.get("name")
    quantity = order.get("quantity")
    if name is None or quantity is None:
        response = json.dumps({"error": {"code": 404, "message": "invalid order"}})
        return response
    msg = "Buy {} {}".format(name, quantity)
    s.send(msg.encode())
    response = s.recv(1024).decode()
    try:
        result = int(response)
    except:
        print(response)
        return response
    s.close()
    if result == 0:  # Successful Buy order
        write_lock = a.gen_wlock()
        with write_lock:  # Acquire lock to ensure mutual exclusion
            with open("./data/orders.txt") as f:
                data = json.load(f)
            id = len(data.get("orders"))
            new_order = {"number": id,
                         "name": name, "quantity": quantity}
            data.get("orders").append(new_order)
            with open("./data/orders.txt", "w") as f:
                json.dump(data, f)
        print(new_order)
        return str(id)
    return str(result)  # Unsuccessful buy order

def getOrder(order_id):
    global a
    read_lock = a.gen_rlock()
    with read_lock:
        with open("./data/orders.txt") as f:
            data = json.load(f)
    l = len(data.get("orders"))
    print("l: {}".format(l))
    if order_id < 0 or order_id >= l:
        return {"error": {"code": 404, "message": "order_id does not exist"}}
    print(data.get("orders")[order_id])
    return data.get("orders")[order_id]


def handleClient(c, addr):  # Function to pass to threads; thread per session model
    # print("Connected to :", addr[0], ":", addr[1])
    incoming = c.recv(1024)
    while incoming:
        # frontend service sends order in form of JSON object
        msg = incoming.decode()
        # POST /orders
        reg = re.compile(r"^processOrder (.+)$")
        match = reg.match(msg) 
        if match:
            order = json.loads(match.group(1))
            response = processOrder(order)
            c.send(response.encode())

        # GET /orders/<order_number>
        reg = re.compile(r"^getOrder (.+)$")
        match = reg.match(msg)
        if match:
            try:
                order_id = int(match.group(1))
                response = json.dumps(getOrder(order_id))
            except:
                response = json.dumps({"error": {"code": 404, "message": "invalid order_id"}}) 
            c.send(response.encode())
        incoming = c.recv(1024)
    c.close()


def main():
    parser = OptionParser()
    parser.add_option('-d', default=1, help='Running on docker', action='store',
                      type='int', dest='d')
    (options, args) = parser.parse_args()
    global d
    d = options.d
    host = '128.119.243.168'  # elnux3 IP
    if d == 1:
        host = socket.gethostbyname(socket.gethostname())
    if d == 2:
        host = '127.0.0.1'  # Run on local machine
    port = 12745
    s = socket.socket()
    s.bind((host, port))
    s.listen(20)
    executor = ThreadPoolExecutor(max_workers=20)
    while True:
        c, addr = s.accept()
        executor.submit(handleClient, c, addr)


if __name__ == "__main__":
    main()
