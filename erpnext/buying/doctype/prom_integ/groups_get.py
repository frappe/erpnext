from dotenv import load_dotenv
from .prom_client.frappeclient import FrappeClient as ERPClient
from .prom_client.prom_sync import EvoClient as PromClient
import os
from pprint import pprint
import frappe
from frappe.utils.password import get_decrypted_password
from frappe.utils import get_host_name

ERP_URL = "https://{}".format(get_host_name())
API_KEY = frappe.db.get_value("Prom settings", "Prom settings", "erp_key")
API_SECRET = get_decrypted_password("Prom settings", "Prom settings", "erp_secret")
conn = ERPClient(ERP_URL, api_key=API_KEY, api_secret=API_SECRET)

AUTH_TOKEN = get_decrypted_password("Prom settings", "Prom settings", "prom_token")
HOST = "my.prom.ua"
p_client = PromClient(AUTH_TOKEN, HOST)


def check_cat_exist(name):
    cat = conn.get_list("Item Group", filters=[["Item Group", "name", "=", name]])
    if cat:
        return True
    else:
        return False


def create_category_prom(name, id):
    if not check_cat_exist(name):
        body = {
            "parent_item_group": "Prom",
            'item_group_name': name,
            'external_id': id,
            'doctype': 'Item Group'   
        }
        return conn.insert(doc=body)


def create_category(name, id, is_group=0, parent="Upcompany"):
    
    if not check_cat_exist(name):
        body = {
            'parent_item_group': parent,
            'item_group_name': name,
            'external_id': id,
            'is_group': is_group,
            'doctype': 'Item Group'   
        }
        return conn.insert(doc=body)
    return None


def get_groups():
    return p_client.make_request("GET", "https://my.prom.ua/api/v1/groups/list?limit=100")['groups']


def get_category():
    prod_list = p_client.get_all_products()
    cat_s = list()
    for i in prod_list:
        category = i['category']
        if not category in cat_s:
            cat_s.append(category)
    # pprint(cat_s)
    return cat_s


def import_groups():
    groups = get_groups()
    group_names = {}
    parent_ids = [p_id['parent_group_id'] for p_id in groups]
    layer_list = []
    for group in groups:
        if not group['parent_group_id']:
            group_names[group['id']] = group['name']
            create_category(group['name'], group['id'], 1)
            print(group_names)
    while len(group_names) < len(groups):
        for i in groups:
            if i['id'] in parent_ids:
                temp_p = 1
            else:
                temp_p = 0
            if i['parent_group_id'] in group_names:
                group_names[i['id']] = i['name']
                create_category(i['name'], i['id'], temp_p, group_names[i['parent_group_id']])
    # print(group_names)



def main():
    if not check_cat_exist("Upcompany"):
        conn.insert(doc={
            "parent_item_group": "All Item Groups",
            'is_group': 1,
            'item_group_name': "Upcompany",
            'doctype': 'Item Group'  
        })
    if not check_cat_exist("Marketplaces"):
        conn.insert(doc={
            "parent_item_group": "All Item Groups",
            'is_group': 1,
            'item_group_name': "Marketplaces",
            'doctype': 'Item Group'  
        })
    if not check_cat_exist("Prom"):
        conn.insert(doc={
                "parent_item_group": "Marketplaces",
                'is_group': 1,
                'item_group_name': "Prom",
                'doctype': 'Item Group'  
            })
        
    cat_s = get_category()

    for i in cat_s:
        create_category_prom(i['caption'], i['id'])

    import_groups()

@frappe.whitelist()
def run():
    main()