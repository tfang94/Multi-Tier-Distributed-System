import socket
from readerwriterlock import rwlock
from concurrent.futures import ThreadPoolExecutor
import json
from optparse import OptionParser
import os

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
    port = 12645
    s = socket.socket()
    s.connect((host, port))  # Connect to catalog service
    name = order.get("name")
    quantity = order.get("quantity")
    msg = "Buy {} {}".format(name, quantity)
    s.send(msg.encode())
    result = int(s.recv(1024))
    s.close()
    if result == 0:  # Successful Buy order
        write_lock = a.gen_wlock()
        with write_lock:  # Acquire lock to ensure mutual exclusion
            with open("./data/orders.txt") as f:
                data = json.load(f)
            id = len(data.get("orders"))
            new_order = {"Order Number": id,
                         "Product Name": name, "Quantity": quantity}
            data.get("orders").append(new_order)
            with open("./data/orders.txt", "w") as f:
                json.dump(data, f)
        print(new_order)
        return str(id)
    return str(result)  # Unsuccessful buy order


def handleClient(c, addr):  # Function to pass to threads; thread per session model
    print("Connected to :", addr[0], ":", addr[1])
    incoming = c.recv(1024)
    while incoming:
        # frontend service sends order in form of JSON object
        order = json.loads(incoming.decode())
        response = processOrder(order)
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
