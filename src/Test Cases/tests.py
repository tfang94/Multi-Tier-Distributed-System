import unittest
import requests
import json
import logging


class Testing(unittest.TestCase):
    logger = logging.getLogger(__name__)
    logging.basicConfig(format='%(asctime)s %(module)s %(levelname)s: %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)

    def __init__(self, *args, **kwargs):
        super(Testing, self).__init__(*args, **kwargs)
        # self.host = '128.119.243.168'  # Uncomment to test elnux3
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


if __name__ == '__main__':
    unittest.main()
