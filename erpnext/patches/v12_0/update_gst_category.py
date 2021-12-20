import frappe


def execute():

    company = frappe.get_all('Company', filters = {'country': 'India'})
    if not company:
        return

    frappe.db.sql(""" UPDATE `tabSales Invoice` set gst_category = 'Unregistered'
        where gst_category = 'Registered Regular'
        and coalesce(customer_gstin, '')=''
        and coalesce(billing_address_gstin,'')=''
    """)

    frappe.db.sql(""" UPDATE `tabPurchase Invoice` set gst_category = 'Unregistered'
        where gst_category = 'Registered Regular'
        and coalesce(supplier_gstin, '')=''
    """)
