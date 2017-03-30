import frappe
from frappe import _
from erpnext.selling.doctype.customer.customer import short_code_generator


def execute():
    frappe.reload_doctype('Customer')
    customers = frappe.get_all('Customer',
                               fields=['name', 'short_code', 'customer_name'])
    for customer in customers:
        frappe.db.set_value('Customer', customer.name,
                            'short_code',
                            short_code_generator(customer.customer_name))
    print(_("Success, Customer Short Codes are generated."))
