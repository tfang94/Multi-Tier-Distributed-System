import socket
from readerwriterlock import rwlock
from concurrent.futures import ThreadPoolExecutor
import json
import re
from optparse import OptionParser
import os
from threading import Thread
import time
import sys
import errno

a = rwlock.RWLockFairD()

def listenMain(main_socket, executor):
    while True:
        c, addr = main_socket.accept()
        executor.submit(handleClient, c, addr)

def listenRestock(restock_socket, executor):
    while True:
        c, addr = restock_socket.accept()
        executor.submit(restock, c)

# Repeats every 10 seconds, checking inventory and restocking any out of stock items back to 100
def restock(c):
    global a
    while True:
        try:
            print("\n--Checking Inventory--")
            write_lock = a.gen_wlock()
            with write_lock:
                with open("./data/catalog.txt") as f:
                    data = json.load(f)
                qMap = data.get("quantity")
                for key in qMap:
                    if qMap.get(key) == 0:
                        print("restocked {}".format(key))
                        qMap[key] = 100
                        msg = key + " " # sometimes multiple messages may be combined into one so add a space to help parse
                        c.send(msg.encode())
                with open("./data/catalog.txt", "w") as f:
                    json.dump(data, f)
            print("\n")
            time.sleep(10)
        except IOError as e:
            if e.errno == errno.EPIPE:
                break


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
    try:
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
    except IOError as e:
        if e.errno == errno.EPIPE:
            return


def main():
    host = '127.0.0.1'
    executor = ThreadPoolExecutor(max_workers=20) # thread pool to handle incoming connections

    # main port for handling query and buy requests from frontend and order service
    port = 12645
    main_socket = socket.socket()
    main_socket.bind((host, port))
    main_socket.listen(20)

    # separate socket for sending restock notifications to front-end
    restock_port = 12545
    restock_socket = socket.socket()
    restock_socket.bind((host, restock_port))
    restock_socket.listen()

    # assign threads to listen for data connections and hand them over to thread pool
    t1 = Thread(target=listenRestock, args=(restock_socket, executor,))
    t2 = Thread(target=listenMain, args=(main_socket, executor,))
    t1.start()
    t2.start()


if __name__ == "__main__":
    main()
