from __future__ import unicode_literals
import frappe

def execute():
    item_tax_template_list = frappe.get_list('Item Tax Template')
    for template in item_tax_template_list:
        doc = frappe.get_doc('Item Tax Template', template.name)
        for tax in doc.taxes:
            doc.company = frappe.get_value('Account', tax.tax_type, 'company')
            break
        doc.save()