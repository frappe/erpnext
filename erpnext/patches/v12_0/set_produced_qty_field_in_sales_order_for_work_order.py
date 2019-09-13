import frappe
from frappe.utils import flt

def execute():
    frappe.reload_doctype('Sales Order Item')
    frappe.reload_doctype('Sales Order')
    work_orders = frappe.db.get_all('Work Order', ['name', 'produced_qty', 'sales_order_item'], {'sales_order_item': ('!=', None)})
    for work_order in work_orders:
        frappe.db.set_value('Sales Order Item', work_order.get('sales_order_item'), 'produced_qty', flt(work_order.get('produced_qty')))