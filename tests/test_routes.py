"""
TestYourResourceModel API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from datetime import date
from urllib.parse import quote_plus
from service import app
from service.models import db, init_db, Product
from service.common import status  # HTTP Status Codes
from tests.factories import ProductFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/testdb"
)
BASE_URL = "/products"


######################################################################
#  T E S T   C A S E S
######################################################################
# pylint: disable=too-many-public-methods
class TestYourResourceServer(TestCase):
    """REST API Server Tests"""

    @classmethod
    def setUpClass(cls):
        """This runs once before the entire test suite"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        # Set up the test database
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        app.logger.setLevel(logging.CRITICAL)
        init_db(app)

    @classmethod
    def tearDownClass(cls):
        """This runs once after the entire test suite"""
        db.session.close()

    def setUp(self):
        """This runs before each test"""
        self.client = app.test_client()
        db.session.query(Product).delete()  # clean up the last tests
        db.session.commit()

    def tearDown(self):
        """This runs after each test"""
        db.session.remove()

    def _create_products(self, count):
        """Factory method to create products in bulk"""
        products = []
        for _ in range(count):
            test_product = ProductFactory()
            response = self.client.post(BASE_URL, json=test_product.serialize())
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test product",
            )
            new_product = response.get_json()
            test_product.id = new_product["id"]
            products.append(test_product)
        return products

    ######################################################################
    #  P L A C E   T E S T   C A S E S   H E R E
    ######################################################################

    def test_index(self):
        """It should call the home page"""
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_get_product_list(self):
        """It should Get a list of Products"""
        self._create_products(5)
        response = self.client.get(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), 5)

    def test_query_product_list_by_category(self):
        """It should Query Product by Category"""
        products = self._create_products(10)
        test_category = products[0].category
        category_products = [
            product for product in products if product.category == test_category
        ]
        response = self.client.get(
            BASE_URL, query_string=f"category={quote_plus(test_category)}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), len(category_products))
        # check the data just to be sure
        for product in data:
            self.assertEqual(product["category"], test_category)

    def test_query_product_list_by_name(self):
        """It should Query Product by Name"""
        products = self._create_products(10)
        test_name = products[0].name
        name_products = [product for product in products if product.name == test_name]
        response = self.client.get(
            BASE_URL, query_string=f"name={quote_plus(test_name)}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(len(data), len(name_products))
        # check the data just to be sure
        for product in data:
            self.assertEqual(product["name"], test_name)

    def test_get_product(self):
        """It should Get a single Product"""
        # get the id of a product
        test_product = self._create_products(1)[0]
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        self.assertEqual(data["name"], test_product.name)

    def test_get_product_not_found(self):
        """It should not Get a Product thats not found"""
        response = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.get_json()
        logging.debug("Response data = %s", data)
        self.assertIn("was not found", data["message"])

    def test_create_product(self):
        """It should Create a new Product"""
        test_product = ProductFactory()
        logging.debug("Test Pet: %s", test_product.serialize())
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["price"], test_product.price)
        self.assertEqual(new_product["category"], test_product.category)
        self.assertEqual(new_product["inventory"], test_product.inventory)
        self.assertEqual(
            date.fromisoformat(new_product["created_date"]), test_product.created_date
        )
        self.assertEqual(
            date.fromisoformat(new_product["modified_date"]), test_product.modified_date
        )

        # Check that the location header was correct
        response = self.client.get(location)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        new_product = response.get_json()
        self.assertEqual(new_product["name"], test_product.name)
        self.assertEqual(new_product["price"], test_product.price)
        self.assertEqual(new_product["category"], test_product.category)
        self.assertEqual(new_product["inventory"], test_product.inventory)
        self.assertEqual(
            date.fromisoformat(new_product["created_date"]), test_product.created_date
        )
        self.assertEqual(
            date.fromisoformat(new_product["modified_date"]), test_product.modified_date
        )

    def test_update_product(self):
        """It should Update an existing Product"""
        # create a product to update
        test_product = ProductFactory()
        response = self.client.post(BASE_URL, json=test_product.serialize())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # update the product
        new_product = response.get_json()
        logging.debug(new_product)
        new_product["category"] = "unknown"
        response = self.client.put(f"{BASE_URL}/{new_product['id']}", json=new_product)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_product = response.get_json()
        self.assertEqual(updated_product["category"], "unknown")

    def test_delete_product(self):
        """It should Delete a Product"""
        test_product = self._create_products(1)[0]
        response = self.client.delete(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(len(response.data), 0)
        # make sure they are deleted
        response = self.client.get(f"{BASE_URL}/{test_product.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_purchase_a_product(self):
        """It should Purchase a Product"""
        product_available = ProductFactory()
        product_available.inventory = 1
        product_available.available = True
        response = self.client.post(BASE_URL, json=product_available.serialize())
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            "Could not create test product",
        )
        new_product_available = response.get_json()
        product_available.id = new_product_available["id"]

        product = product_available
        response = self.client.put(f"{BASE_URL}/{product.id}/purchase")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(f"{BASE_URL}/{product.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.get_json()
        logging.debug("Response data: %s", data)
        self.assertEqual(data["available"], False)

    def test_purchase_a_product_unavailable(self):
        """It should not Purchase a Product that is not available"""
        product_unavailable = ProductFactory()
        product_unavailable.inventory = 0
        product_unavailable.available = False
        response = self.client.post(BASE_URL, json=product_unavailable.serialize())
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            "Could not create test product",
        )
        new_product_unavailable = response.get_json()
        product_unavailable.id = new_product_unavailable["id"]

        response = self.client.put(f"{BASE_URL}/{product_unavailable.id}/purchase")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    ######################################################################
    #  T E S T   S A D   P A T H S
    ######################################################################

    def test_create_product_no_data(self):
        """It should not Create a Product with missing data"""
        response = self.client.post(BASE_URL, json={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_product_no_content_type(self):
        """It should not Create a Product with no content type"""
        response = self.client.post(BASE_URL)
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_create_product_wrong_content_type(self):
        """It should not Create a Product with the wrong content type"""
        response = self.client.post(BASE_URL, data="hello", content_type="text/html")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_purchase_product_no_data(self):
        """It should not Purchase a Product with the wrong id"""
        bad_id = 999999
        response = self.client.put(f"BASE_URL/{bad_id}/purchase")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_product_not_found(self):
        """It should not Update a Product thats not found"""
        test_product = ProductFactory()
        response = self.client.put(
            f"{BASE_URL}/{test_product.id}", json=test_product.serialize()
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.get_json()
        logging.debug("Response data = %s", data)
        self.assertIn("was not found", data["message"])

    # def test_create_product_bad_price(self):
    #     """It should not Create a Product with bad available data"""
    #     test_product = ProductFactory()
    #     logging.debug(test_product)
    #     # change price to a string
    #     test_product.price = "true"
    #     response = self.client.post(BASE_URL, json=test_product.serialize())
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # def test_create_product_bad_inventory(self):
    #     """It should not Create a Pet with bad gender data"""
    #     product = ProductFactory()
    #     logging.debug(product)
    #     # change gender to a bad string
    #     test_product = product.serialize()
    #     test_product["inventory"] = "male"    # wrong case
    #     response = self.client.post(BASE_URL, json=test_product)
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
