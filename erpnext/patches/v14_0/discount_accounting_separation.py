import frappe

def execute():
    doc = frappe.get_doc("Accounts Settings")
    discount_account = doc.enable_discount_accounting
    if discount_account:
        buying_settings = frappe.get_doc("Buying Settings", "Buying Settings")
        selling_settings = frappe.get_doc("Selling Settings", "Selling Settings")

        buying_settings.enable_discount_accounting = 1
        selling_settings.enable_discount_accounting = 1

        buying_settings.save()
        selling_settings.save()