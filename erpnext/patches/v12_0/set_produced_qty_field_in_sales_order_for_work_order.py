import frappe
from frappe.utils import flt

def execute():
    frappe.reload_doctype('Sales Order Item')
    frappe.reload_doctype('Sales Order')
    sales_order_items = frappe.db.get_all('Sales Order Item', ['name'])
    for so_item in sales_order_items:
        #for multiple work orders against same sales invoice item
        linked_wo_with_so_item = frappe.db.get_all('Work Order', ['produced_qty', 'sales_order_item'], {
            'sales_order_item': so_item.get('name'),
            'docstatus': 1
        })
        if len(linked_wo_with_so_item) > 0:
            total_produced_qty = 0
            for wo in linked_wo_with_so_item:
                total_produced_qty += flt(wo.get('produced_qty'))
            frappe.db.set_value('Sales Order Item', so_item.get('name'), 'produced_qty', total_produced_qty)
            frappe.db.commit()