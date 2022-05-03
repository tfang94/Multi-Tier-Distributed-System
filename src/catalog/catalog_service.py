import socket
from readerwriterlock import rwlock
from concurrent.futures import ThreadPoolExecutor
import json
import re
from optparse import OptionParser
import os
from threading import Timer

a = rwlock.RWLockFairD()

def restock():
    global a
    Timer(10.0, restock).start()
    print("----------------------------------------------")
    print("Checking Inventory:")
    write_lock = a.gen_wlock()
    with write_lock:
        with open("./data/catalog.txt") as f:
            data = json.load(f)
        qMap = data.get("quantity")
        for key in qMap:
            if qMap.get(key) == 0:
                print("restocked {}".format(key))
                qMap[key] = 100
        with open("./data/catalog.txt", "w") as f:
            json.dump(data, f)
    print("----------------------------------------------\n")


def Query(name):  # Returns dictionary representing JSON object
    global a
    read_lock = a.gen_rlock()
    with read_lock:  # Acquire lock for mutual exclusion
        with open("./data/catalog.txt", "r") as f:
            data = json.load(f)
    quantity = data.get("quantity").get(name)
    price = data.get("price").get(name)
    if quantity is not None:
        result = {"name": name, "price": price, "quantity": quantity}
        # print(result)
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
    # print("Connected to :", addr[0], ":", addr[1])
    incoming = c.recv(1024)
    while incoming:
        # Parse message and call Query()
        msg = incoming.decode()
        print(msg)
        x = re.split("\s", msg)
        if x[0] == "Query":
            response = json.dumps(Query(x[1]))
        if x[0] == "Buy":
            try:
                name = x[1]
                req_qty = int(x[2])
                response = str(Buy(name, req_qty))
            except:
                response = json.dumps({"error": {"code": 404, "message": "invalid quantity requested"}})
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

    restock() # continuously checks and restocks out of stock item every 10 seconds
    host = '128.119.243.168'  # elnux3 IP
    if d == 1:
        host = socket.gethostbyname(socket.gethostname())  # Run on Docker
    if d == 2:
        host = '127.0.0.1'  # Run on local machine
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
