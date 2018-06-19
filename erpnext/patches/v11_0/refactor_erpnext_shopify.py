from __future__ import unicode_literals
import frappe
from frappe.installer import remove_from_installed_apps

def execute():
	frappe.reload_doc('erpnext_integrations', 'doctype', 'shopify_settings')
	frappe.reload_doc('erpnext_integrations', 'doctype', 'shopify_tax_account')
	frappe.reload_doc('erpnext_integrations', 'doctype', 'shopify_log')
	frappe.reload_doc('erpnext_integrations', 'doctype', 'shopify_webhook_detail')

	if 'erpnext_shopify' in frappe.get_installed_apps():
		remove_from_installed_apps('erpnext_shopify')

		frappe.db.sql('delete from `tabDesktop Icon` where app="erpnext_shopify" ')
		frappe.delete_doc("Module Def", 'erpnext_shopify')

		frappe.db.commit()

		frappe.db.sql("truncate `tabShopify Log`")

		setup_app_type()

def setup_app_type():
	shopify_settings = frappe.get_doc("Shopify Settings")
	shopify_settings.app_type = 'Private'
	shopify_settings.update_price_in_erpnext_price_list =  0 if getattr(shopify_settings, 'push_prices_to_shopify', None) else 1
	shopify_settings.flags.ignore_mandatory = True
	shopify_settings.ignore_permissions = True
	shopify_settings.save()
