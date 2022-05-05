import unittest
import requests
import json
import logging
import time


class Testing(unittest.TestCase):
    logger = logging.getLogger(__name__)
    logging.basicConfig(format='%(asctime)s %(module)s %(levelname)s: %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)

    def __init__(self, *args, **kwargs):
        super(Testing, self).__init__(*args, **kwargs)
        self.host = '127.0.0.1'
        self.port = 8001

    # Check JSON item returned after normal GET request
    def test_Query_normal(self):
        URL = "http://{}:{}/products/{}".format(self.host, self.port, "Tux")
        r = requests.get(URL)
        data = json.loads(r.content.decode())
        name = data.get("name")
        price = data.get("price")
        quantity = data.get("quantity")
        self.assertEqual(name != None and price !=
                         None and quantity != None, True)

    # Check JSON item returned after invalid GET request
    def test_Query_invalid_product(self):
        URL = "http://{}:{}/products/{}".format(
            self.host, self.port, "invalid_product")
        r = requests.get(URL)
        data = json.loads(r.content.decode())
        self.assertEqual(data.get("error").get("message"), "product not found")

    # Verify POST order behavior.  Query an item, run two POST orders (to see if state is persistent),
    # check quantity and returned order number
    def test_Post_normal(self):
        # Get initial quanity
        URL = "http://{}:{}/products/{}".format(self.host, self.port, "Tux")
        r = requests.get(URL)
        data = json.loads(r.content.decode())
        quantity_initial = data.get("quantity")

        # Post request 1
        URL = "http://{}:{}/orders".format(self.host, self.port)
        order = {"name": "Tux", "quantity": 2}
        r = requests.post(URL, order)
        order_id1 = int(r.content.decode())

        # Post request 2
        order = {"name": "Tux", "quantity": 3}
        r = requests.post(URL, order)
        order_id2 = int(r.content.decode())

        # Get final quanity
        URL = "http://{}:{}/products/{}".format(self.host, self.port, "Tux")
        r = requests.get(URL)
        data = json.loads(r.content.decode())
        quantity_final = data.get("quantity")

        # Check catalog.txt persistent and decrementing properly
        self.assertEqual(quantity_initial - quantity_final, 5)

        # Check returned Order ID persistent in orders.txt and entries adding properly
        self.assertEqual(order_id2 - order_id1, 1)

    # POST order for invalid product should return same JSON error as GET
    def test_Post_invalid_product(self):
        URL = "http://{}:{}/orders".format(self.host, self.port)
        order = {"name": "invalid_product", "quantity": 2}
        r = requests.post(URL, order)
        data = json.loads(r.content.decode())
        self.assertEqual(data.get("error").get("message"), "product not found")

    # POST order with quantity exceeding current stock
    def test_Post_out_of_stock(self):
        # Get initial quanity
        URL = "http://{}:{}/products/{}".format(self.host, self.port, "Tux")
        r = requests.get(URL)
        data = json.loads(r.content.decode())
        quantity = data.get("quantity")

        URL = "http://{}:{}/orders".format(self.host, self.port)
        order = {"name": "Tux", "quantity": quantity + 1}
        r = requests.post(URL, order)
        data = json.loads(r.content.decode())
        self.assertEqual(data.get("error").get(
            "message"), "product out of stock")

    # GET /orders<order_number> with valid input
    def test_Get_order_normal(self):
        # Post an order and call Get and verify that it matches
        URL = "http://{}:{}/orders".format(self.host, self.port)
        order = {"name": "Chess", "quantity": 1}
        r = requests.post(URL, order)
        order_id = int(r.content.decode())

        # Verify that GET /orders<order_number> returns correct result
        URL = "http://{}:{}/orders/{}".format(self.host, self.port, order_id)
        r = requests.get(URL)
        query_result = json.loads(r.content.decode())
        self.assertEqual(query_result.get("name"), "Chess")
        self.assertEqual(int(query_result.get("quantity")), 1)

    # GET /orders<order_number> with out of bounds order_id
    def test_get_order_out_of_bounds_id(self):
        # Post an order to get latest id
        URL = "http://{}:{}/orders".format(self.host, self.port)
        order = {"name": "Chess", "quantity": 1}
        r = requests.post(URL, order)
        order_id = int(r.content.decode())

        # Call Get order on 1 + max id
        URL = "http://{}:{}/orders/{}".format(self.host, self.port, order_id + 1)
        r = requests.get(URL)
        query_result = json.loads(r.content.decode())
        expected = {"error": {"code": 404, "message": "order_id does not exist"}}
        self.assertEqual(query_result, expected)

    # GET /orders<order_number> with invalid order_id input (i.e. string instead of int)
    def test_get_order_invalid_input(self):
        URL = "http://{}:{}/orders/{}".format(self.host, self.port, "invalid input")
        r = requests.get(URL)
        query_result = json.loads(r.content.decode())
        expected = {"error": {"code": 404, "message": "invalid order_id"}}
        self.assertEqual(query_result, expected)

    # test that catalog restocks every 10 seconds when an item is out of stock
    def test_restock(self):
        # Get initial quanity
        URL = "http://{}:{}/products/{}".format(self.host, self.port, "Monopoly")
        r = requests.get(URL)
        data = json.loads(r.content.decode())
        quantity = data.get("quantity")

        # Post order to buy all of the remaining quantity to set it to 0
        URL = "http://{}:{}/orders".format(self.host, self.port)
        order = {"name": "Monopoly", "quantity": quantity}
        r = requests.post(URL, order)

        # wait 10 seconds for catalog to restock
        print("--waiting 10 seconds for testing restock--")
        time.sleep(10)

        # Check quantity
        URL = "http://{}:{}/products/{}".format(self.host, self.port, "Monopoly")
        r = requests.get(URL)
        data = json.loads(r.content.decode())
        final_quantity = data.get("quantity")
        self.assertEqual(int(final_quantity), 100)

    # Cache test - cache runs in background, so manual test with print statements and screenshots verify that it
    #   is working as intended.  That is, query methods update the cache, cache is referenced if the key exists
    #   and invalidation flag is not True.  Buy and restock set the invalidation flag to true.  The screenshot shows
    #   that the first queries are not cached (print "cache miss") since the cache is still empty.  Afterwards, print "cache hit"
    #   shows that cache is being used.  However, after buy requests, we see that print "cache miss" will occur due to the invalidation flag
    #   and it is only reset after query call.  To verify these tests, uncomment the print statements in frontend_service.py under
    #   httpHandler class

    # Replication tests - replication was also tested manually with screenshots.  It works for running all 3 replicas, but for simplicity
    #   the screenshots show replica2 out of date upon starting and replica3 with up to date version.  After starting both, replica 2 automatically
    #   syncs up with replica3.  Although not captured in the screenshot, I tested with both orders of starting replica 2 first or later and 
    #   regardless of order, the sync works as intended
    #   I then ran client.py and screenshots verify that only replica3 (leader node) handles and updates the new orders.  replica2
    #   doesn't handle the order but after calling client, it is also updated with the latest orders verifying that the leader
    #   propogates the order as intended after each successful Buy

    # fault tolerance test - done manually with screenshots.  I ran replica3 with simulate failure flag -f 1 (optional command line arg)
    #   then I ran the client and also had replica2 running.  It showed that replica3 crashed after 5 orders, a leader election occurred
    #   and replica2 handled the reset of the orders.  From the client side, none of this was visible


if __name__ == '__main__':
    unittest.main()
