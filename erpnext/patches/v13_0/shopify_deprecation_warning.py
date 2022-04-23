import click
import frappe


def execute():

	frappe.reload_doc("erpnext_integrations", "doctype", "shopify_settings")
	if not frappe.db.get_single_value("Shopify Settings", "enable_shopify"):
		return

	click.secho(
		"Shopify Integration is moved to a separate app and will be removed from ERPNext in version-14.\n"
		"Please install the app to continue using the integration: https://github.com/frappe/ecommerce_integrations",
		fg="yellow",
	)
