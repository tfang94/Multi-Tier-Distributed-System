import requests
import json
import socket
from optparse import OptionParser
import random
from scipy.stats import bernoulli
import time


def main():
    # Optional command line arguments for probability p of order and length of session n
    parser = OptionParser()
    parser.add_option('-p', default=0.7, help='Parameter for probability of sending order request', action='store',
                      type='float', dest='p')
    parser.add_option('-n', default=50, help='Number of iterations of request cycles for session', action='store',
                      type='int', dest='n')
    parser.add_option('-d', default=1, help='Running on Docker or Elnux3', action='store',
                      type='int', dest='d')
    (options, args) = parser.parse_args()
    p = options.p  # Parameter for probability of sending order request
    n = options.n  # Number of iterations of request cycles for session
    d = options.d  # D=1 (Server on Docker), D=0 (Server on Elnux3)

    query_cnt = 0
    buy_cnt = 0
    getOrder_cnt = 0
    query_time = 0
    buy_time = 0
    getOrder_time = 0
    query_start = 0
    query_end = 0
    getOrder_start = 0
    buy_start = 0
    buy_end = 0
    getOrder_end = 0
    

    with requests.Session() as s:  # Session of requests using same connection
        localOrderHistory = []
        nameList = ["Tux", "Whale", "Elephant", "Bird", "Lego", "Frisbee", "Barbie", "Monopoly", "Marbles", "Chess"]
        for i in range(n):  # Sequence of n queries and (potential) buy requests
            # Randomly query frontend server
            randIndex = random.randint(0, 9)
            name = nameList[randIndex]
            host = '128.119.243.168'  # elnux3 IP
            if d == 1:
                host = '127.0.0.1'  # Run on Docker or local machine
            port = 8001
            URL = "http://{}:{}/products/{}".format(
                host, port, name)
            # Only start measuring latency after first iteration since there is a sync up period in the first round
            if i > 0:
                query_start = time.time()
            r1 = s.get(URL)  # Queries item
            data = json.loads(r1.content.decode())
            if i > 0:
                query_end = time.time()
                query_cnt += 1
                query_time += query_end - query_start
            print("Query response: {}".format(data))
            if data.get("quantity") > 0:
                if bernoulli.rvs(p):  # Order based on bernoulli(p) random variable
                    URL = "http://{}:{}/orders".format(host, port)
                    order = {"name": name, "quantity": 1}
                    if i > 0:
                        buy_start = time.time()
                    r2 = s.post(URL, order)
                    post_result = r2.content.decode()
                    if i > 0:
                        buy_end = time.time()
                        buy_cnt += 1
                        buy_time += buy_end - buy_start
                    try:
                        order_id = int(post_result)
                        localOrderHistory.append({"number": order_id, "name": name, "quantity": 1})
                        print("Order successful; ID = {}".format(order_id))
                    except:
                        print(post_result)

    # Before exiting verify local order history matches order query requests to server
    print("\n")
    print("--verifying local order history matches query order requests to server--")
    print("Local order history size: {}".format(len(localOrderHistory)))
    matches = True
    for order in localOrderHistory:
        URL = "http://{}:{}/orders/{}".format(host, port, order.get("number"))

        getOrder_start = time.time()
        r3 = s.get(URL)
        query_result = json.loads(r3.content.decode())
        getOrder_end = time.time()
        getOrder_cnt += 1
        getOrder_time += getOrder_end - getOrder_start

        if order.get("name") != query_result.get("name") or order.get("quantity") != int(query_result.get("quantity")):
            matches = False
            print("mismatch for order {}".format(order.get("number")))
    if matches:
        print("verified - all orders match\n")

    print("\nResults:\n--------------------------------------------------------------")
    average_query_time = query_time / query_cnt
    print("Average Query Time: {}".format(average_query_time))
    if (buy_cnt > 0 and getOrder_cnt > 0):
        average_buy_time = buy_time / buy_cnt
        average_getOrder_time = getOrder_time / getOrder_cnt
        print("Average Buy Time: {}".format(average_buy_time))
        print("Average getOrder Time: {}".format(average_getOrder_time))
        print("\n")


if __name__ == "__main__":
    main()
