from pprint import pprint
from datetime import datetime
from loguru import logger
from .prom_client.frappeclient import FrappeClient as ERPClient
from .prom_client.prom_sync import EvoClient as PromClient
from .prom_client.structures import webitem_uom, prom_presence
from frappe.utils.password import get_decrypted_password
from frappe.utils import get_host_name
from .groups_get import main as group_get
import frappe

logger.add('logs/prod_{time}.log')
ERP_URL = 'https://{}'.format(get_host_name())
API_KEY = frappe.db.get_value('Prom settings', 'Prom settings', 'erp_key')
API_SECRET = get_decrypted_password('Prom settings', 'Prom settings', 'erp_secret')
conn = ERPClient(ERP_URL, api_key=API_KEY, api_secret=API_SECRET)

AUTH_TOKEN = get_decrypted_password('Prom settings', 'Prom settings', 'prom_token')
HOST = 'my.prom.ua'
print(AUTH_TOKEN)
p_client = PromClient(AUTH_TOKEN, HOST)

def check_file(name):
    res = conn.get_doc('File', filters=[['File', 'file_name', '=', name]])
    if res:
        return True
    else:
        return False

def create_file(website_image, name):
    if not check_file(website_image.split('/')[-1]):
        conn.insert({
            'doctype': 'File',
            'file_name': website_image.split('/')[-1],
            'file_url': website_image,
            'attached_to_doctype': 'Website Item',
            'attached_to_field': 'website_image',
            'attached_to_name': name
        })


def webitem_exists(item_prom):
    logger.info(item_prom['external_id'])
    
    erp_item = calculate_item(item_prom)
    erp_webitem, website_image = calculate_website_item(item_prom)
    webitem_erp = []

    item_erp = conn.get_list('Item', filters=[['Item', 'name', '=', item_prom['sku']]])
    if item_erp:
        # logger.info('Updating Item!')
        conn.update(erp_item, 'Item', item_prom['sku'])
    else:
        # logger.info('Creating Item.')
        conn.insert(erp_item)

    if item_prom['external_id']:
        webitem_erp = conn.get_list(
            'Website Item',
            filters=[['Website Item', 'name', '=', item_prom['external_id']]])
    if not webitem_erp:
        webitem_erp = conn.get_list(
            'Website Item',
            filters=[['Website Item', 'item_code', '=', item_prom['sku']]])
    if webitem_erp:
        webitem_erp = webitem_erp[0]
        # logger.info('Website Item updating!')
        if website_image:
            create_file(website_image, webitem_erp.get('name'))
        erp_webitem['website_image'] = website_image
        conn.update(erp_webitem, 'Website Item', webitem_erp.get('name'))
    else:
        logger.info('Website item creation.')
        name = conn.insert(erp_webitem)
        name = name['name']
        if website_image:
            create_file(website_image, name)
        conn.update({'website_image': website_image}, 'Website Item', name)
    
        
    item_price = conn.get_list(
        'Item Price',
        filters=[['Item Price', 'item_code', '=', item_prom['sku']]]
        )
    if not item_price:
        # logger.info('Item Price not found')
        conn.insert(calculate_item_price(item_prom))
    else:
        # logger.info('Item Price updated')
        conn.update(calculate_item_price(item_prom), 'Item Price', item_price[0].get('name'))

def calculate_item_price(item_prom):
    body = {
        'item_code': item_prom['sku'],
        'uom': webitem_uom[item_prom['measure_unit']],
        'price_list_rate': item_prom['price'],
        'price_list': 'Prom Selling',
        'doctype': 'Item Price'
    }
    return body

def calculate_item(item_prom):
    # Ukrainian Item translation
    translation_uk = p_client.get_product_translation(item_prom['id'], 'uk')
    body = {
        'item_code': item_prom['sku'],
        'item_name': item_prom['name_multilang']['uk'],
        'description': translation_uk['description'],
        # Be sure that the group exists, you can use 'get_groups' script if not
        'item_group': item_prom['group']['name'],
        'stock_uom': webitem_uom[item_prom['measure_unit']],
        'search_requests': translation_uk['keywords'],
        'doctype': 'Item'
    }
    return body

def calculate_website_item(item_prom):
    translation_uk = p_client.get_product_translation(item_prom['id'], 'uk')
    body = {
        'item_code': item_prom['sku'],
        'item_name': item_prom['name_multilang']['uk'],
        'website_item_name_ukr': item_prom['name_multilang']['uk'],
        'search_requests': translation_uk['keywords'],
        'discount': item_prom['discount'],
        'availability': prom_presence[item_prom['presence']],
        'marketplace_category': item_prom['category']['caption'],
        'translation': [
            {'language': 'ru',
            'specific_name': item_prom['name_multilang']['ru'],
            'specific_description': item_prom['description'],
            'search_requests': item_prom['keywords']
            }
        ],
        'doctype': 'Website Item'
    }
    if item_prom['regions']:
        body['county_of_origin'] = item_prom['regions'][0]['uk']
    if item_prom['selling_type'] == 'retail':
        body['selling_type'] = 'Роздріб'
    elif item_prom['selling_type'] == 'universal':
        logger.info('Оптом та в роздріб')
        body['selling_type'] = 'Оптом та в роздріб'
        body['wholesale_price'] = item_prom['prices']
    if item_prom['images']:
        for i in item_prom['images']:
            del i['thumbnail_url']
        website_image = item_prom['images'][0]['url']
        body['website_image'] = website_image
        if len(item_prom['images']) >= 2:
            body['images'] = item_prom['images'][1:]
        if website_image:
            return body, website_image
    return body, None


@frappe.whitelist()
def main():
    logger.info('Starting...')
    start_time = datetime.now()
    not_imported_items = []
    group_get()
    product_list = p_client.get_all_products()
    for product in product_list:
        try:
            if product['status'] == 'on_display':
                webitem_exists(product)
        except Exception as e:
            not_imported_items.append(product['id'])
            logger.error(f'{e}!')
        # if product['status'] == 'on_display':
        #     webitem_exists(product)

    # test_product = p_client.get_product_by_id(1849252909)['product']
    # pprint(test_product)
    # webitem_exists(test_product)  
    
    logger.info(datetime.now() - start_time)
    if not_imported_items:
        # Some item's won't be imported`
        return 1
    else:
        # OK
        return 0
    
        
    
    
