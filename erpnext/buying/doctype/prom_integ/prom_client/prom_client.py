import json
import http.client
from requests_toolbelt.multipart.encoder import MultipartEncoder
import requests


class HTTPError(Exception):
    pass


class EvoClient(object):
    def __init__(self, token, host="my.prom.ua"):
        self.token = token
        self.host = host
        self.headers = {
            "Authorization": "Bearer {}".format(self.token),
            "Content-type": "application/json",
        } 

    def make_request(self, method, url, body=None):
        connection = http.client.HTTPSConnection(self.host)

        if body:
            body = json.dumps(body)

        connection.request(method, url, body=body, headers=self.headers)
        response = connection.getresponse()
        if response.status != 200:
            raise HTTPError("{}: {}".format(response.status, response.reason))

        response_data = response.read()
        return json.loads(response_data.decode())
    
    def import_file_to_prom(self, file_path="bin/Test_import.csv"):
        encoder = MultipartEncoder(
            fields={"data": str({
                        "force_update": True,
                        "only_available": False,
                        "mark_missing_product_as": "none"}),
                    "file": ("import.csv", open(file_path, "rb"), "text/csv")}
            )
        self.headers['Content-Type'] = encoder.content_type
        response = requests.post(
            'https://my.prom.ua/api/v1/products/import_file',
            data=encoder,
            headers=self.headers
            )
        # id = dict(response.text)["id"]
        # status = self.import_status_check(id)
        return response

    def get_order_list(self):
        url = "/api/v1/orders/list"
        method = "GET"

        return self.make_request(method, url)

    def get_order(self, order_id):
        url = "/api/v1/orders/{id}"
        method = "GET"

        return self.make_request(method, url.format(id=order_id))

    def set_order_status(
        self, status, ids, cancellation_reason=None, cancellation_text=None
    ):
        url = "/api/v1/orders/set_status"
        method = "POST"

        body = {"status": status, "ids": ids}
        if cancellation_reason:
            body["cancellation_reason"] = cancellation_reason

        if cancellation_text:
            body["cancellation_text"] = cancellation_text

        return self.make_request(method, url, body)

    def get_product_list(self, limit=200):
        url = "/api/v1/products/list?limit={}".format(limit)
        method = "GET"

        return self.make_request(method, url)

    def get_product_by_id(self, product_id):
        url = "/api/v1/products/{id}"
        method = "GET"

        return self.make_request(method, url.format(id=product_id))

    def get_product_by_sku(self, sku):
        url = "/api/v1/products/sku/{sku}"
        method = "GET"

        return self.make_request(method, url.format(sku=sku))

    def get_product_by_barcode(self, barcode):
        url = "/api/v1/products/barcode/{barcode}"
        method = "GET"

        return self.make_request(method, url.format(barcode=barcode))

    def get_product_by_url(self, url):
        url = "/api/v1/products/url/{url}"
        method = "GET"

        return self.make_request(method, url.format(url=url))

    def get_product_by_name(self, name):
        url = "/api/v1/products/name/{name}"
        method = "GET"

        return self.make_request(method, url.format(name=name))

    def edit_product_description(self, product_id, description):

        url = "/api/v1/products/edit"
        method = "POST"

        body = [{"id": product_id, "description": description}]

        return self.make_request(method, url, body)

    def edit_search_terms(self, product_id, *args):
        url = "/api/v1/products/edit"
        method = "POST"

        body = [{"id": product_id, "search_terms": args}]

        return self.make_request(method, url, body)

    def edit_product_price(self, product_id, new_price):
        url = "/api/v1/products/edit"
        method = "POST"
        body = [{"id": product_id, "price": new_price}]

        return self.make_request(method, url, body)

    def edit_product_quantity(self, product_id, new_quantity):
        url = "/api/v1/products/edit"
        method = "POST"
        body = [{"id": product_id, "quantity_in_stock": new_quantity}]

        return self.make_request(method, url, body)

    def edit_product_status(self, product_id, new_status):
        url = "/api/v1/products/edit"
        method = "POST"
        body = [{"id": product_id, "status": new_status}]

        return self.make_request(method, url, body)

    def edit_product_name(self, product_id, new_name):
        url = "/api/v1/products/edit"
        method = "POST"
        body = [{"id": product_id, "name": new_name}]

        return self.make_request(method, url, body)

    def edit_product_keywords(self, product_id, *args):
        url = "/api/v1/products/edit"
        method = "POST"
        body = [{"id": product_id, "keywords": args}]

        return self.make_request(method, url, body)

    def get_product_categories(self):
        url = "/api/v1/products/categories"
        method = "GET"

        return self.make_request(method, url)

    def get_product_category(self, category_id):
        url = "/api/v1/products/categories/{id}"
        method = "GET"

        return self.make_request(method, url.format(id=category_id))

    def get_product_category_by_name(self, category_name):
        url = "/api/v1/products/categories/name/{name}"
        method = "GET"

        return self.make_request(method, url.format(name=category_name))

    def get_product_category_by_url(self, category_url):
        url = "/api/v1/products/categories/url/{url}"
        method = "GET"

        return self.make_request(method, url.format(url=category_url))

    def get_product_category_by_parent(self, parent_id):
        url = "/api/v1/products/categories/parent/{id}"
        method = "GET"

        return self.make_request(method, url.format(id=parent_id))

    def get_product_category_by_parent_name(self, parent_name):
        url = "/api/v1/products/categories/parent/name/{name}"
        method = "GET"

        return self.make_request(method, url.format(name=parent_name))

    def get_product_category_by_parent_url(self, parent_url):
        url = "/api/v1/products/categories/parent/url/{url}"
        method = "GET"

        return self.make_request(method, url.format(url=parent_url))

    def get_product_category_by_parent_id(self, parent_id):
        url = "/api/v1/products/categories/parent/{id}"
        method = "GET"

        return self.make_request(method, url.format(id=parent_id))

    def set_product_category(self, product_id, category_id):
        url = "/api/v1/products/categories/set"
        method = "POST"

        body = [{"product_id": product_id, "category_id": category_id}]

        return self.make_request(method, url, body)

    def get_product_images(self, product_id):
        url = "/api/v1/products/images/{id}"
        method = "GET"

        return self.make_request(method, url.format(id=product_id))

    def set_product_images(self, product_id, *args):
        url = "/api/v1/products/images/set"
        method = "POST"

        body = [{"product_id": product_id, "images": args}]

        return self.make_request(method, url, body)

    def get_product_variants(self, product_id):
        url = "/api/v1/products/variants/{id}"
        method = "GET"

        return self.make_request(method, url.format(id=product_id))

    def set_product_variants(self, product_id, *args):
        url = "/api/v1/products/variants/set"
        method = "POST"

        body = [{"product_id": product_id, "variants": args}]

        return self.make_request(method, url, body)

    def get_product_options(self, product_id):
        url = "/api/v1/products/options/{id}"
        method = "GET"

        return self.make_request(method, url.format(id=product_id))
