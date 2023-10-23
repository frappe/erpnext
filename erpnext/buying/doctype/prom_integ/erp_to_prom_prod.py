from pprint import pprint
from .prom_client.frappeclient import FrappeClient as ERPClient
from .prom_client.prom_sync import EvoClient as PromClient
from .prom_client.structures import prom_translate, webitem_fields, stock_uom
import pandas as pd
import re
import os
from loguru import logger
from dotenv import load_dotenv
from datetime import datetime, timedelta
import frappe
from frappe.utils.password import get_decrypted_password
from frappe.utils import get_host_name
import pytz
import time

ERP_URL = "https://{}".format(get_host_name())
API_KEY = frappe.db.get_value("Prom settings", "Prom settings", "erp_key")
API_SECRET = get_decrypted_password("Prom settings", "Prom settings", "erp_secret")
conn = ERPClient(ERP_URL, api_key=API_KEY, api_secret=API_SECRET)

AUTH_TOKEN = get_decrypted_password("Prom settings", "Prom settings", "prom_token")
HOST = "my.prom.ua"
p_client = PromClient(AUTH_TOKEN, HOST)
logger.add("logs/prod_{time}.log")

def get_doctype_list(doctype, fields, filters=[]):
    return conn.get_list(
        doctype,
        fields=fields,
        filters=filters,
        limit_page_length=5000
    )

def get_images(name):
    images = conn.get_list(
        "Website Item",
        fields=["images.url", "website_image"],
        filters=[["Website Item", "name", "=", name]]
        )
    main_image = conn.get_list(
        "Website Item",
        fields=["website_image"],
        filters=[["Website Item", "name", "=", name]]
        )
    if main_image:
        main_image = [main_image[0]["website_image"]]
    else:
        main_image = []
    images = [image['url'] for image in images][::-1]
    images = main_image + images
    # logger.debug(images) 
    if images:
        return ", ".join(str(image) for image in images)
    else:
        return None

def get_group_ids(group_name):
    groups = conn.get_list(
        "Item Group",
        fields=["external_id"],
        filters=[["Item Group", "name", "=", group_name]]
        )
    if groups:
        return groups[0]['external_id']
    else:
        return None

def get_prices(name):
    prices = conn.get_list(
        "Website Item",
        fields=["wholesale_price.minimum_order_quantity", "wholesale_price.price"],
        filters=[["Website Item", "name", "=", name]]
        )
    return prices

def cleanhtml(raw_html):
    CLEANR = re.compile('<.*?>')
    cleantext = re.sub(CLEANR, '', raw_html)
    return cleantext


# Calculate str timestamp 2 hours ago from now
two_hours_ago_time = datetime.now(pytz.timezone('Europe/Kiev')) - timedelta(hours=1)

# Get items from ERPNEXT DocType
web_items = get_doctype_list('Website Item', webitem_fields, [["Website Item", "modified", ">", str(two_hours_ago_time)]])
item_price = get_doctype_list('Item Price', ["item_code", "price_list_rate", "currency"])

web_items = pd.DataFrame(web_items)
item_price = pd.DataFrame(item_price)


def prom_preparing(web_items):
    # Adding source address to images 
    
    # web_items["website_image"] = web_items["website_image"].apply(
    #     lambda x: "https://my.upcompany.online" + x if x else None)

    # Merge and replacing stock uom to prom template
    web_items = web_items.merge(item_price, on="item_code", how="left")
    web_items['stock_uom'] = web_items['stock_uom'].replace('штук', 'шт.')
    web_items['stock_uom'] = web_items['stock_uom'].replace('шт', 'шт.')
    web_items['stock_uom'] = web_items['stock_uom'].replace('метров', 'м.')
    web_items['stock_uom'] = web_items['stock_uom'].replace('кг', 'кг.')
    web_items['stock_uom'] = web_items['stock_uom'].replace('метров', 'м.')
    web_items['stock_uom'] = web_items['stock_uom'].replace('грам', 'гр.')
    web_items['discount'] = web_items['discount'].replace('%0', None)
    web_items['discount'] = web_items['discount'].replace('0', None)
    web_items['selling_type'] = web_items['selling_type'].replace('Роздріб', 'r')
    web_items['selling_type'] = web_items['selling_type'].replace('Опт', 'w')
    web_items['selling_type'] = web_items['selling_type'].replace('Оптом та в роздріб', 'u')

    web_items['Оптова_ціна'] = None
    web_items['Мінімальне_замовлення_опт'] = None
    
    for index, web_item in web_items.iterrows():
        web_items.loc[index, 'item_group'] = get_group_ids(web_items.loc[index, 'item_group'])
        logger.info(web_item['website_image'])
        # if web_items.loc[index, 'website_image']:
        #     web_items.loc[index, 'website_image'] += get_images(web_item['name'])
        web_images = get_images(web_item['name'])
        web_items.loc[index, 'stock_uom'] = stock_uom[web_items.loc[index, 'stock_uom']]
        print(web_items.loc[index, 'stock_uom'])
        if web_images and web_items.loc[index, 'website_image']:
            web_items.loc[index, 'website_image'] += ", " + web_images
        wholesale_prices = get_prices(web_item['name'])
        temp_price = []
        temp_quantity = []
        for price in wholesale_prices:
            temp_price.append(price['price'])
            temp_quantity.append(price['minimum_order_quantity'])
        if temp_price and \
            (web_items.loc[index, 'selling_type'] == 'w' or \
            web_items.loc[index, 'selling_type'] == 'u'):
            if max(temp_price) < web_items.loc[index, 'price_list_rate']:
                temp_price = list(map(str, temp_price))
                web_items.loc[index, 'Оптова_ціна'] = ";".join(temp_price[::-1])
                web_items.loc[index, 'Мінімальне_замовлення_опт'] = ";".join(temp_quantity[::-1])

    # Translate all fields to prom template 
    web_items = web_items.rename(columns=prom_translate)
    
    # web_items['Пошукові_запити_укр'] = web_items['Пошукові_запити']
    # web_items['Опис_укр'] = web_items['Опис']
    # web_items['Назва_позиції_укр'] = web_items['Назва_позиції']

    return web_items


def get_created_items_descr(items):
    """ Return: A list with items' external id and full description """
    context = []
    for i in range(len(items)):
        item_id = items.iloc[i]['Ідентифікатор_товару']
        item_description = items.iloc[i]['Опис']
        print(item_description)
        item = {'id': item_id, 'description': item_description}
        context.append(item)
    return context

def check_dir(name):
    if os.path.exists(name) and os.path.isdir(name):
        return True
    else:
        os.mkdir(name)
        return True
        

def main(web_items):
   
    if not web_items.empty:
        web_items = prom_preparing(web_items)
        check_dir('bin')
        web_items.to_csv('bin/web_items.csv', index=False)
        response = p_client.import_file_to_prom("bin/web_items.csv").json()
        
        # frappe.msgprint(f'{response}')
        return response

@frappe.whitelist()
def run():
    
    doc = frappe.new_doc("Prom Import Status")
    doc.status = "Processing"
    doc.save()
    try:
        response = main(web_items)
        if not response:
            return 2
        if response.get('error'):
            print(response['error'])
            doc.status = "Fatal"
            doc.save()
            return 1
        else:
            print(response)
        import_id = response.get("id")
        if import_id:
            doc.import_id = import_id
            doc.save()
            frappe.enqueue('erpnext.buying.doctype.prom_integ.erp_to_prom_prod.check_import_status', 
                queue='long', timeout=1200, is_async=True, import_id=import_id, doc=doc)
    except Exception as err:
        doc.status = "Fatal"
        doc.save()
        return 1
    return 0
   


def check_import_status(import_id, doc):
    def set_doc(status, response):
        doc.status = status
        doc.total = response.get("total")
        if response.get("errors"):
            doc.logs = f"{response.get('errors')}"
        doc.save()
    while True:
        response = p_client.import_status_check(import_id)
        if response.get("status") == "FATAL" or response.get("status") == "FAIL":
            set_doc("Fatal", response)
            break
        elif response.get("status") == "PARTIAL":
            set_doc("Partial", response)
            break
        elif response.get("status") == "SUCCESS" and \
                response.get("total") <= \
                sum([response.get("imported"), response.get("with_errors_count")]):
            set_doc("Success", response)
            break
        time.sleep(150)

    



