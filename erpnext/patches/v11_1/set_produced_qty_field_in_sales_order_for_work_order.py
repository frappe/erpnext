import frappe
from erpnext.selling.doctype.sales_order.sales_order import update_produced_qty_in_so_item

def execute():
    frappe.reload_doctype('Sales Order Item')
    frappe.reload_doctype('Sales Order')
    sales_order_items = frappe.db.get_all('Sales Order Item', ['name'])
    for so_item in sales_order_items:
        update_produced_qty_in_so_item(so_item.get('name'))