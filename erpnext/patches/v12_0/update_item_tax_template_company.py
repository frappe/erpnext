from __future__ import unicode_literals
import frappe

def execute():
    frappe.reload_doc('accounts', 'doctype', 'item_tax_template')

    item_tax_template_list = frappe.get_list('Item Tax Template')
    for template in item_tax_template_list:
        doc = frappe.get_doc('Item Tax Template', template.name)
        for tax in doc.taxes:
            doc.company = frappe.get_value('Account', tax.tax_type, 'company')
            break
        doc.save()