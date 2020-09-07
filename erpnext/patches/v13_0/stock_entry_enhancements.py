# Copyright(c) 2020, Frappe Technologies Pvt.Ltd.and Contributors
# License: GNU General Public License v3.See license.txt

from __future__ import unicode_literals
import frappe

def execute():
    frappe.reload_doc("stock", "doctype", "stock_entry")
    if frappe.db.has_column("Stock Entry", "add_to_transit"):
        frappe.db.sql("""
            UPDATE `tabStock Entry` SET 
            stock_entry_type = 'Material Transfer',
            purpose = 'Material Transfer',
            add_to_transit = 1 WHERE stock_entry_type = 'Send to Warehouse'
            """)

        frappe.db.sql("""UPDATE `tabStock Entry` SET 
            stock_entry_type = 'Material Transfer',
            purpose = 'Material Transfer'
            WHERE stock_entry_type = 'Receive at Warehouse'
            """)
        
        frappe.reload_doc("stock", "doctype", "warehouse_type")
        if not frappe.db.exists('Warehouse Type', 'Transit'):
            doc = frappe.new_doc('Warehouse Type')
            doc.name = 'Transit'
            doc.insert()

        frappe.reload_doc("stock", "doctype", "stock_entry_type")
        frappe.delete_doc_if_exists("Stock Entry Type", "Send to Warehouse")
        frappe.delete_doc_if_exists("Stock Entry Type", "Receive at Warehouse")