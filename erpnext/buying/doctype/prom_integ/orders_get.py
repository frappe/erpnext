from dotenv import load_dotenv
from .prom_client.frappeclient import FrappeClient as ERPClient
from .prom_client.prom_sync import EvoClient as PromClient
import os
import json
from datetime import datetime
from pprint import pprint
import frappe
from loguru import logger
from frappe.utils.password import get_decrypted_password
from frappe.utils import get_host_name

ERP_URL = "https://{}".format(get_host_name())
API_KEY = frappe.db.get_value("Prom settings", "Prom settings", "erp_key")
API_SECRET = get_decrypted_password("Prom settings", "Prom settings", "erp_secret")
conn = ERPClient(ERP_URL, api_key=API_KEY, api_secret=API_SECRET)

AUTH_TOKEN = get_decrypted_password("Prom settings", "Prom settings", "prom_token")
HOST = "my.prom.ua"
p_client = PromClient(AUTH_TOKEN, HOST)

def log_output(message):
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    print(now + " - " + message)


def get_prom_order(limit=50):
    '''
    :param limit: count of orders to return
    :return: list of last prom orders
    '''
    return p_client.get_orders(limit=limit)['orders']


def clients_to_json(client_info):
    with open("clients.json", "a", encoding="utf-8") as output:
        json.dump(client_info, output, ensure_ascii=False)
        output.write(",\n")


def create_shipping_address(delivery_address, full_name):
    comma_index = delivery_address.find(',')
    body = {
        'address_line1': "Нова пошта" + delivery_address[comma_index+1:],
        'city': delivery_address[:comma_index],
        'country': 'Ukraine',
        'address_type': 'Shipping',
        'links': [{
            'link_name': full_name,
            'link_doctype': 'Customer',
            'doctype': 'Dynamic Link'
        }], 
        'doctype': 'Address'
    }
    return conn.insert(doc=body)


def create_customer(client_info):
    body = {
        'customer_name': client_info['client_full_name'],
        'customer_type': 'Individual',
        'territory': 'Ukraine',
        'customer_details': client_info['comment'],
        'customer_group': 'Individual',
        'doctype': 'Customer'   
    }
    return conn.insert(doc=body)


def edit_customer_contact(client_info):
    pass


def create_customer_contact(client_info):
    body = {
        'first_name': client_info['first_name'],
        'last_name': client_info['last_name'],
        'links': [{
            'link_name': client_info['client_full_name'],
            'link_doctype': 'Customer',
            'doctype': 'Dynamic Link'
        }], 
        'doctype': 'Contact'
    }
    phones = []
    emails = []
    for i in client_info['phones']:
        phones.append({
            'doctype': 'Contact Phone',
            'phone': i
        })
    for i in client_info['emails']:
        emails.append({
            'doctype': 'Contact Email',
            'email_id': i
        })
    body['phone_nos'] = phones
    body['email_ids'] = emails
    return conn.insert(doc=body)


def customer_exists(client_info, delivery_address, delivery_option):
    client_erp = conn.get_doc("Customer", client_info['client_full_name']).get('name')
    client_contact_erp = conn.get_list(
        "Contact",
        filters=[
            ["Contact Phone", "phone", "in", client_info['phones']]
        ]
        )
    if client_info["emails"]:
        client_email_erp = conn.get_list(
            "Contact",
            filters=[
                ["Contact Email","email_id","in", client_info["emails"]]
            ])
    else:
        client_email_erp = None

    if client_erp and (client_contact_erp or client_email_erp):
        print("Customer and their contact exists")
    else:
        if not client_erp:
            create_customer(client_info)
        if (not client_contact_erp and client_info['phones']) or \
            (not client_email_erp and client_info["emails"]):
            create_customer_contact(client_info)
            if delivery_option == 'Доставка "Нова Пошта"':
                create_shipping_address(
                    delivery_address,
                    client_info['client_full_name']
                    )
        
def add_all_clients():
    orders = get_prom_order(5)
    for order in orders:
        client_id = order['client_id']
        client_prom = p_client.get_client_by_id(client_id)['client']
        print(client_prom['last_name']+" "+client_prom['first_name'])
        customer_exists(
        client_prom,
        order['delivery_address'],
        order['delivery_option']['name']
        )

def create_sales_order(client_info, order):
    customer_exists(
        client_info,
        order['delivery_address'],
        order['delivery_option']['name']
        )
    order_time_created = datetime.strptime(order['date_created'], "%Y-%m-%dT%X.%f+00:00")
    body = {
        'customer': client_info['client_full_name'],
        'transaction_date': order_time_created.strftime("%Y-%m-%d"),
        'company': 'Up_Company',
        'currency': 'UAH',
        'territory': 'Ukraine',
        'order_type': 'Sales',
        'contact_email': order['email'],
        'contact_mobile': order['phone'],
        'conversion_rate': 0.4035,
        'items': [],
        'doctype': 'Sales Order'
    }
    for item in order['products']:
        print(f"{item}")
        item_erp = conn.get_list(
            'Website Item',
            filters=[['Website Item', 'item_code', '=', item['sku']]])
        if item_erp:
            item_erp = item_erp[0]
        else:
            frappe.msgprint("Product not found.")
        # item_erp = conn.get_doc('Website Item', item['external_id'])
        if item_erp.get('item_code'):
            item_price = conn.get_doc(
                'Item Price',
                filters=[['Item Price', 'item_code', '=', item_erp['item_code']]],
                fields=['price_list_rate']
                )
            body['items'].append({
                'delivery_date': '2023-01-31', 
                'item_code': item_erp['item_code'],
                'qty': int(item['quantity']),
                'rate': item_price[0]['price_list_rate'],
                'warehouse': 'All Warehouses - UpC',
                'doctype': 'Sales Order Item'
            })
    return conn.insert(doc=body)

@frappe.whitelist()
def main():
    order = get_prom_order()[0]

    client_id = order['client_id']
    client_prom = p_client.get_client_by_id(client_id)['client']
    print(client_prom['last_name']+" "+client_prom['first_name'])
    # customer_exists(
    #     client_prom,
    #     order['delivery_address'],
    #     order['delivery_option']['name']
    #     )

    response = create_sales_order(client_prom, order)

# Black d (pip)
if __name__ == "__main__":
    main()
