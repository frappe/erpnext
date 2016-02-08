from __future__ import unicode_literals
import pdb
import frappe,json
from frappe import _, msgprint, throw

def get_customer_series(doc, method=None):

    #print doc.custom_series
    if doc.custom_series == None:
        prefix = get_prefix(doc)
        series = get_series(doc, prefix)
        check_duplicates(doc)
        doc.name=series
        doc.custom_series = series
        return doc
    elif doc.custom_series != doc.name:
        doc.name = doc.custom_series
        return doc


def get_prefix(doc):
    if doc.doctype == 'Customer':
        #frappe.msgprint(doc.customer_type)
        prefix = doc.customer_name[:3]
        if doc.customer_type == 'Company':
            #frappe.msgprint(doc.customer_name)
            customerNameCount = frappe.db.sql("select count(`name`) as n from `tabCustomer` where customer_name = '" + doc.customer_name + "'")[0][0]
            #frappe.msgprint(customerNameCount)
            if customerNameCount >0:
                frappe.throw(_("Duplicate company name."))
        else:
            customerNameCount = frappe.db.sql("select count(`name`) as n, tax_id from `tabCustomer` where customer_name = '" + doc.customer_name + "'", as_dict=1)[0]
            #frappe.msgprint(customerNameCount)
            if customerNameCount['n'] >0:
                if doc.tax_id != None or doc.tax_id !='':
                    if customerNameCount['tax_id'] != '' and customerNameCount['tax_id'] == doc.tax_id:
                        frappe.throw(_("Duplicate company name."))
                else:
                    if customerNameCount['tax_id'] == '':
                        frappe.throw(_("Duplicate company name."))

        if doc.tax_id != '' or doc.tax_id != None:
            customerNameCount = frappe.db.sql("select count(`name`) as n from `tabCustomer` where tax_id = '" + doc.tax_id + "'")[0][0]
            #frappe.msgprint(customerNameCount)
            if customerNameCount >0:
                frappe.throw(_("Duplicate company name with tax_id = " + doc.tax_id))

    elif doc.doctype == 'Supplier':
        prefix = doc.supplier_name[:3]
        #supplierNameCount = frappe.db.sql("select count(`name`) as n from `tabSupplier` where supplier_name = '" + doc.supplier_name + "'")[0][0]
        #if supplierNameCount >0:
        #    frappe.throw(_("Duplicate company name."))
    elif doc.doctype == 'Contact':
        prefix = doc.first_name[:3]

    return prefix

def get_series(doc, prefix):
    countCustomer = frappe.db.sql("select count(`name`) as n from `tabCustomer` where customer_name like '" + prefix.upper() + "%'")[0][0]
    countSupplier = frappe.db.sql("select count(`name`) as n from `tabSupplier` where supplier_name like '" + prefix.upper() + "%'")[0][0]
    countContact = frappe.db.sql("select count(`name`) as n from `tabContact` where first_name like '" + prefix.upper() + "%'")[0][0]
    count = countCustomer + countContact + countSupplier + 1
    #frappe.msgprint(count)
    series = prefix.upper() + '{:03d}'.format(count)

    while 1:
        countCustomer = frappe.db.sql("select count(`name`) as n from `tabCustomer` where name = '" + series + "'")[0][0]
        countSupplier = frappe.db.sql("select count(`name`) as n from `tabSupplier` where name = '" + series + "'")[0][0]
        countContact = frappe.db.sql("select count(`name`) as n from `tabContact` where name = '" + series + "'")[0][0]

        if countCustomer + countSupplier + countContact != 0:
            count = count + 1
            #frappe.msgprint(count)
            series = prefix.upper() + '{:03d}'.format(count)
        else:
            break


    return series

def check_duplicates(doc):
    pass