import socket
from readerwriterlock import rwlock
from concurrent.futures import ThreadPoolExecutor
import json
import re
from optparse import OptionParser
import os

a = rwlock.RWLockFairD()

def Query(name):  # Returns dictionary representing JSON object
    global a
    read_lock = a.gen_rlock()
    with read_lock:  # Acquire lock for mutual exclusion
        with open("./data/catalog.txt", "r") as f:
            data = json.load(f)
    quantity = data.get("quantity").get(name)
    price = data.get("price").get(name)
    if quantity:
        result = {"name": name, "price": price, "quantity": quantity}
        print(result)
        return result
    else:  # Return error as JSON if product doesn't exist
        return {"error": {"code": 404, "message": "product not found"}}


def Buy(name, req_qty):  # If in stock, decrements quantity of toy in catalog.txt by req_qty
    global a
    write_lock = a.gen_wlock()
    with write_lock:  # Acquire lock for mutual exclusion
        with open("./data/catalog.txt") as f:
            data = json.load(f)
        quantity = data.get("quantity").get(name)
        if quantity is None:
            return -1  # Product not found error
        if req_qty <= quantity:  # Check if enough in stock
            data.get("quantity")[name] -= req_qty
            with open("./data/catalog.txt", "w") as f:
                json.dump(data, f)
            return 0  # Success
    return -2  # Product out of stock error


def handleClient(c, addr):  # Function to pass to threads; thread per session model
    print("Connected to :", addr[0], ":", addr[1])
    incoming = c.recv(1024)
    while incoming:
        # Parse message and call Query()
        msg = incoming.decode()
        print(msg)
        x = re.split("\s", msg)
        if x[0] == "Query":
            response = json.dumps(Query(x[1]))
        if x[0] == "Buy":
            response = str(Buy(x[1], int(x[2])))
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
    port = 12645
    s = socket.socket()
    s.bind((host, port))
    s.listen(20)
    executor = ThreadPoolExecutor(max_workers=20)
    while True:
        c, addr = s.accept()
        executor.submit(handleClient, c, addr)


if __name__ == "__main__":
    main()
