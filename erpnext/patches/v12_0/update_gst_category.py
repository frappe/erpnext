from __future__ import unicode_literals
import frappe

def execute():

    company = frappe.get_all('Company', filters = {'country': 'India'})
    if not company:
        return

    frappe.db.sql(""" UPDATE `tabSales Invoice` set gst_category = 'Unregistered'
        where gst_category = 'Registered Regular'
        and ifnull(customer_gstin, '')=''
        and ifnull(billing_address_gstin,'')=''
    """)

    frappe.db.sql(""" UPDATE `tabPurchase Invoice` set gst_category = 'Unregistered'
        where gst_category = 'Registered Regular'
        and ifnull(supplier_gstin, '')=''
    """)