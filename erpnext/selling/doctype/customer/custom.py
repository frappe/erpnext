from __future__ import unicode_literals
import frappe
from frappe import _, msgprint, throw

def get_customer_series(doc, method=None):
    frappe.debug_log(doc)
    #if doc.name == '':
    prefix = get_prefix(doc)
    series = get_series(doc, prefix)
    check_duplicates(doc)
    doc.name=series
    return doc


    #frappe.throw(_("cannot save"))

def get_prefix(doc):
    if doc.doctype == 'Customer':
        prefix = doc.customer_name[:3]
    elif doc.doctype == 'Supplier':
        prefix = doc.supplier_name[:3]
    elif doc.doctype == 'Contact':
        prefix = doc.first_name[:3]

    return prefix

def get_series(doc, prefix):
    countCustomer = frappe.db.sql("select count(`name`) as n from `tabCustomer` where customer_name like '" + prefix.upper() + "%'")[0][0]
    countSupplier = frappe.db.sql("select count(`name`) as n from `tabSupplier` where supplier_name like '" + prefix.upper() + "%'")[0][0]
    countContact = frappe.db.sql("select count(`name`) as n from `tabContact` where first_name like '" + prefix.upper() + "%'")[0][0]
    count = countCustomer + countContact + countSupplier + 1
    series = prefix.upper() + '{:03d}'.format(count)

    while 1:
        countCustomer = frappe.db.sql("select count(`name`) as n from `tabCustomer` where name = '" + series + "'")[0][0]
        countSupplier = frappe.db.sql("select count(`name`) as n from `tabSupplier` where name = '" + series + "'")[0][0]
        countContact = frappe.db.sql("select count(`name`) as n from `tabContact` where name = '" + series + "'")[0][0]

        if countCustomer + countSupplier + countContact != 0:
            count = count + 1
            series = prefix.upper() + '{:03d}'.format(count)
        else:
            break


    return series

def check_duplicates(doc):
    pass