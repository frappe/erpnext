from requests_toolbelt.multipart.encoder import MultipartEncoder
import requests
import json
import http.client
import csv



# settings load env
class HTTPError(Exception):
    pass


class EvoClient(object):
    def __init__(self, token, host="my.prom.ua"):
        self.token = token
        self.host = host
        self.headers = {
            "Authorization": "Bearer {}".format(self.token),
            "accept": "application/json"
        }

    def make_request(self, method, url, body=None):
        connection = http.client.HTTPSConnection(self.host)
        self.headers['Content-Type'] = "application/json"
        if body:
            body = json.dumps(body)

        connection.request(method, url, body=body, headers=self.headers)
        self.response = connection.getresponse()
        if self.response.status != 200:
            raise HTTPError("{}: {}".format(self.response.status, self.response.reason))
        return json.loads(self.response.read().decode())
    
    def get_product_by_id(self, product_id):
        method, url = "GET", "/api/v1/products/{id}"
        return self.make_request(method, url.format(id=product_id))
    
    def get_product_by_external_id(self, external_id):
        method, url = "GET", "/api/v1/products/by_external_id/{id}"
        return self.make_request(method, url.format(id=external_id))

    def get_product_list(self, limit=100):
        # return list of products (only 100 products)
        url = "/api/v1/products/list?limit={}".format(limit)
        method = "GET"
        return self.make_request(method, url)
    
    def get_all_products(self):
        list_products = []
        i = 0
        while True:
            if i == 0:
                list_products.extend(self.get_product_list()['products'])
            else:
                last_id = list_products[-1]['id']
                temp_list = self.make_request(
                        "GET",
                        "/api/v1/products/list?limit=100&last_id={id}".format(id=last_id)
                        )['products']
                list_products.extend(temp_list)
            i += 1
            if len(list_products) == i*100:
                continue
            else:
                return list_products

    def get_product_translation(self, id, language):
        url = "/api/v1/products/translation/{id}?lang={lang}"
        method = "GET"
        return self.make_request(method, url.format(id=id, lang=language))

    def get_product_options(self, product_id):
        url = "/api/v1/products/options/{id}"
        method = "GET"

        return self.make_request(method, url.format(id=product_id))

    def update_prom_item(self, body):
        response = self.make_request("POST", "/api/v1/products/edit", body=body)
        return response

    def update_item_by_extarnal_id(self, body):
        response = self.make_request("POST", "/api/v1/products/edit_by_external_id", body=body)
        return response
    
    def import_file_to_prom(self, file_path=""):
        fields={"data": {
                        "force_update": True,
                        "only_available": False,
                        "mark_missing_product_as": "none",
                        "updated_fields":[
                            "name",
                            "sku",
                            "price",
                            "images_urls",
                            "presence",
                            "quantity_in_stock",
                            "description",
                            "group",
                            "keywords",
                            "attributes",
                            "discount",
                            "labels"
                            ]},
                    "file": ("web_items.csv", open(file_path, "rb"), "text/csv")}
        fields['data'] = json.dumps(fields['data'])
        encoder = MultipartEncoder(fields)
        self.headers['Content-Type'] = encoder.content_type
        response = requests.post(
            'https://my.prom.ua/api/v1/products/import_file',
            data=encoder,
            headers=self.headers
            )
        # id = dict(response.text)["id"]
        # status = self.import_status_check(id)
        return response
    
    def import_status_check(self, id):
        # Check and return import status
        method, url = "GET", "/api/v1/products/import/status/{id}"
        return self.make_request(method, url.format(id=id))

    def get_orders(self, limit:int=1):
        url = f"/api/v1/orders/list?limit={limit}" if limit else "/api/v1/orders/list"
        return self.make_request("GET", url)
    
    def get_client_by_id(self, id):
        url = "/api/v1/clients/{id}".format(id=id)
        return self.make_request("GET", url)
