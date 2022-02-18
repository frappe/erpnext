import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field


def execute():
    company = frappe.get_all('Company', filters = {'country': 'India'})

    if not company:
        return

    create_custom_field('Delivery Note', {
        'fieldname': 'ewaybill',
        'label': 'E-Way Bill No.',
        'fieldtype': 'Data',
        'depends_on': 'eval:(doc.docstatus === 1)',
        'allow_on_submit': 1,
        'insert_after': 'customer_name_in_arabic',
        'translatable': 0,
        'owner': 'Administrator'
    })
