import click
import frappe


def execute():
	if "webshop" in frappe.get_installed_apps():
		return

	if not frappe.db.table_exists("Website Item"):
		return

	doctypes = [
		"E Commerce Settings",
		"Website Item",
		"Recommended Items",
		"Item Review",
		"Wishlist Item",
		"Wishlist",
		"Website Offer",
		"Website Item Tabbed Section",
	]

	for doctype in doctypes:
		frappe.delete_doc("DocType", doctype, ignore_missing=True)

	click.secho(
		"ECommerce is renamed and moved to a separate app"
		"Please install the app for ECommerce features: https://github.com/frappe/webshop",
		fg="yellow",
	)
