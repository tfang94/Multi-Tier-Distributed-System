import socket
from readerwriterlock import rwlock
from concurrent.futures import ThreadPoolExecutor
import json
from optparse import OptionParser
import os
import re
from threading import Thread

a = rwlock.RWLockFairD()
rep_id = 3 # Unique ID for this replica
leader_id = 0 # unitialized leader_id; determined by frontend calling leader election

# Use different ports for different purposes (i.e. order requests, leader election, synchronizing data)
port_map_main = {} # main channel for handling order requests; key refers to replica id
port_map_leader = {} # for leader election
port_map_sync = {} # data synchronization


def initializeRepMap():
    global port_map_main
    global port_map_leader
    global port_map_sync
    port_map_main[1] = 11111
    port_map_main[2] = 11112
    port_map_main[3] = 11113
    port_map_leader[1] = 21111
    port_map_leader[2] = 21112
    port_map_leader[3] = 21113
    port_map_sync[1] = 31111
    port_map_sync[2] = 31112
    port_map_sync[3] = 31113
    
def listenMain(main_socket, executor):
    while True:
        c, addr = main_socket.accept()
        executor.submit(handleClient, c, addr)

# Upon starting, each replica will contact the others to synchronize data to latest version.  Each replica is constantly listening for others
def listenSync(sync_socket, executor):
    while True:
        c, addr = sync_socket.accept()
        executor.submit(syncDataListener, c)

# Each replica is constantly listening for leader election from frontend
def listenLeader(leader_socket, executor):
    while True:
        c, addr = leader_socket.accept()
        executor.submit(handleLeaderElection, c)

def syncPush():
    global rep_id
    global port_map_sync
    for rid in port_map_sync:
        if rep_id != rid: # contact other replicas
            host = '127.0.0.1'
            port = port_map_sync[rid]
            s = socket.socket()
            try:
                s.connect((host, port))
                syncDataPusher(s, rid)
            except ConnectionRefusedError:
                pass # replica not online yet

def syncDataListener(c):
    read_lock = a.gen_rlock()
    write_lock = a.gen_wlock()
    with read_lock:
        with open("./data/orders.txt") as f:
            data = json.load(f)
    order_length = len(data.get("orders"))
    # compare latest order_id and sync to latest
    incoming = json.loads(c.recv(1024).decode())
    incoming_rid = incoming.get("rid")
    incoming_order_length = incoming.get("order_length")
    print("\n--syncing with ID {}--".format(incoming_rid))

    if order_length == incoming_order_length: # no need to sync
        msg = "equal"
        print("data already in sync\n")
        c.send(msg.encode())
    elif order_length < incoming_order_length: # update to pusher's file
        diff = incoming_order_length - order_length
        msg = "push me " + str(diff) # request missing entries
        c.send(msg.encode())
        incoming = json.loads(c.recv(65536).decode()) # maximum TCP buffer size; likely enough for our purposes to be sent in one pass
        requested_entries = incoming.get("requested_entries")
        data.get("orders").extend(requested_entries) # append to orders list
        with write_lock:
            with open("./data/orders.txt", "w") as f:
                json.dump(data, f)
        print("updated with {} entries from ID {}\n".format(diff, incoming_rid))
    else:
        diff = order_length - incoming_order_length
        requested_entries = data.get("orders")[-diff:]
        d_req = {}
        d_req["requested_entries"] = requested_entries
        msg = "requested entries: " + json.dumps(d_req) 
        c.send(msg.encode())
        print("sent {} entries to ID {}\n".format(diff, incoming_rid))
    c.close()

def syncDataPusher(s, listening_rid):
    global rep_id
    print("\n--syncing with ID {}--".format(listening_rid))
    read_lock = a.gen_rlock()
    write_lock = a.gen_wlock()
    with read_lock:
        with open("./data/orders.txt") as f:
            data = json.load(f)
    order_length = len(data.get("orders"))
    msg = {"rid": rep_id, "order_length": order_length}
    s.send(json.dumps(msg).encode())
    # listening side will compare results and send reply
    incoming = s.recv(65536).decode()
    if incoming == "equal":
        print("data already in sync\n")
    reg = re.compile(r"^push me (.+)$")
    match = reg.match(incoming)
    if match: # listener requests entries
        diff = int(match.group(1))
        requested_entries = data.get("orders")[-diff:]
        d_req = {}
        d_req["requested_entries"] = requested_entries
        s.send(json.dumps(d_req).encode())
        print("sent {} entries to ID {}\n".format(diff, listening_rid))
    reg = re.compile(r"requested entries: (.+)$")
    match = reg.match(incoming)
    if match: # listener has additional entries and pushes them
        req_json = json.loads(match.group(1))
        requested_entries = req_json.get("requested_entries")
        data.get("orders").extend(requested_entries) # append to orders list
        with write_lock:
            with open("./data/orders.txt", "w") as f:
                json.dump(data, f)
        print("updated with {} entries from ID {}\n".format(len(requested_entries), listening_rid))
    s.close()


def handleLeaderElection(c):
    global leader_id
    incoming = c.recv(1024).decode()
    # frontend pings replicas starting with highest ID
    if incoming == "ping":
        msg = "present"
        c.send(msg.encode())
    # if new leader elected, notifies all replicas
    reg = re.compile(r"^New Leader: (.+)$")
    match = reg.match(incoming) 
    if match:
        leader_id = int(match.group(1))
        print("\n--New Leader Elected--")
        print("new leader ID is {}\n".format(leader_id))
    c.close()

def processOrder(order):
    # Input: dictionary
    # Output: order ID
    # Polls catalog_service to see if in stock.  If so, tell catalog_service to decrement toy quantity.
    # Then create new order entry in order.txt
    global a
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
    if order_id < 0 or order_id >= l:
        return {"error": {"code": 404, "message": "order_id does not exist"}}
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
    global port_map_main
    global port_map_leader
    global port_map_sync
    global rep_id

    initializeRepMap()
    syncPush()

    host = '127.0.0.1'
    executor = ThreadPoolExecutor(max_workers=20) # thread pool to handle incoming connections

    # Main socket for handling queries with frontend and catalog
    port = port_map_main[rep_id]
    main_socket = socket.socket()
    main_socket.bind((host, port))
    main_socket.listen(20)

    # Socket for synchronizing with other replicas
    port = port_map_sync[rep_id]
    sync_socket = socket.socket()
    sync_socket.bind((host, port))
    sync_socket.listen()

    # Socket for leader election
    port = port_map_leader[rep_id]
    leader_socket = socket.socket()
    leader_socket.bind((host, port))
    leader_socket.listen()

    # assign 2 threads to listen for sync data connections and main connections
    t1 = Thread(target=listenSync, args=(sync_socket, executor,))
    t2 = Thread(target=listenMain, args=(main_socket, executor,))
    t3 = Thread(target=listenLeader, args=(leader_socket, executor,))
    t1.start()
    t2.start()
    t3.start()


if __name__ == "__main__":
    main()
