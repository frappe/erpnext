import frappe
import json
import math
# from frappe.utils import getdate
def get_context(context):
    context.items = frappe.get_list("Item", filters={'show_in_website': 1}, fields=["item_name", "item_code","website_image"])
    #context.warehouse = order_warehouse()


@frappe.whitelist()
def make_so(item_list):
    customer_name = None
    all_contact_doc_name = frappe.db.get_all("Contact",{"user":frappe.session.user},['user','name'])
    for con in all_contact_doc_name:
        # try:
        contact_doc = frappe.get_doc("Contact", con)
        link_table = contact_doc.get('links')
        if(len(link_table) > 0):
            customer_name = link_table[0].get('link_name')
    item_with_all_data = []
    for item in json.loads(item_list):
        if (item.get("qty")):
            if int(item.get('qty')) > 0:
                fetch_details = frappe.db.get_value("Item",{"item_code" : item.get('item_code')},["item_name", "item_code","website_image"])
                item['item_name'] = fetch_details[0]
                item['website_image'] = fetch_details[2]
                item_with_all_data.append(item)
    cache = frappe.cache()
    so = frappe.new_doc("Sales Order")
    so.company = frappe.db.sql("select name from `tabCompany`;")[0][0]

    get_price_list = frappe.db.get_single_value("Bulk Order Settings", "price_list")
    if not get_price_list:
        frappe.throw('Please select price list in <b> Bulk Order Settings</b>')
    so.customer = customer_name
    so.price_list = get_price_list
    so.order_type = "Shopping Cart"
    so.transaction_date = frappe.utils.nowdate()
    del_date = None
    del_date = cache.get_value("del_date")
    if not del_date:
        del_date = frappe.utils.nowdate()
    website_warehouse = frappe.db.get_single_value("Bulk Order Settings", 'default_warehouse')
    for data in json.loads(item_list):
        if (data.get("qty")):
            if(int(data.get("qty")) > 0):
                if not website_warehouse:
                    m = "warehouse not found for item {0} <br> please set default warehouse in bulk order settings ".format(data.get("item_code"))
                    msg = {
                        'status': False,
                        'msg': m
                    }
                    return msg
                item_rate = None
                all_customer_pricing_rule = frappe.db.get_all("Customer Pricing Rule", {'customer': customer_name}, ['name'])
                for rule in all_customer_pricing_rule:
                    doc = frappe.get_doc('Customer Pricing Rule', {'name': rule.get('name')})
                    for item in doc.get('item_details'):
                        #pass
                        if(item.get('item') == data.get('item_code')):
                            item_rate = item.get('list_price')
                
                get_price_list = frappe.db.get_single_value("Bulk Order Settings", 'price_list')
                if not item_rate:
                    item_rate = frappe.db.get_value("Item Price", {'item_code':data.get('item_code'),'price_list': get_price_list} , "price_list_rate")
                
                item = {
                "item_code" : data.get("item_code"),
                "delivery_date" : del_date,
                "qty" : data.get("qty"),
                "rate" : item_rate,
                "warehouse" : website_warehouse
                }
                so.append("items", item)
    try:
        so.insert(ignore_permissions=True)
        cache.set_value('so_name', so.name)
        for item in so.items:
            for i in item_with_all_data:
                if (i.get('item_code') == item.get('item_code')):
                    i['rate'] = item.get('rate')
                    i['amount'] = item.get('amount')
        cache.set_value('item_list', item_with_all_data)
        cache.set_value('rounded_up_total', so.rounded_total)
        cache.set_value('rounding_adjustment', so.rounding_adjustment)
        cache.set_value('total_amount', so.grand_total)
        cache.set_value('default_cust_add', so.customer_address)
        cache.set_value('default_ship_add', so.shipping_address_name)
        return {
            'status': True,
            'so_name': so.name
        }
    except:
        return False

@frappe.whitelist()
def handle_date(date):
    frappe.cache().set_value("del_date", date)


