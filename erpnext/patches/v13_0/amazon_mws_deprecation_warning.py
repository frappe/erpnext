import click
import frappe


def execute():

	frappe.reload_doc("erpnext_integrations", "doctype", "amazon_mws_settings")
	if not frappe.db.get_single_value("Amazon MWS Settings", "enable_amazon"):
		return

	click.secho(
		"Amazon MWS Integration is moved to a separate app and will be removed from ERPNext in version-14.\n"
		"Please install the app to continue using the integration: https://github.com/frappe/ecommerce_integrations",
		fg="yellow",
	)
