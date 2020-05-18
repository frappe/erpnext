from __future__ import unicode_literals
import frappe

def execute():
    invalid_selling_item_price = frappe.db.sql(
        """SELECT name FROM `tabItem Price` WHERE selling = 1 and buying = 0 and (supplier IS NOT NULL or supplier = '')"""
    )
    invalid_buying_item_price = frappe.db.sql(
        """SELECT name FROM `tabItem Price` WHERE selling = 0 and buying = 1 and (customer IS NOT NULL or customer = '')"""
    )
    docs_to_modify = invalid_buying_item_price + invalid_selling_item_price
    for d in docs_to_modify:
        # saving the doc will auto reset invalid customer/supplier field
        doc = frappe.get_doc("Item Price", d[0])
        doc.save()