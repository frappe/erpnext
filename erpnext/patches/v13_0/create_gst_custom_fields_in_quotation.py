import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	company = frappe.get_all("Company", filters={"country": "India"}, fields=["name"])
	if not company:
		return

	sales_invoice_gst_fields = [
		dict(
			fieldname="billing_address_gstin",
			label="Billing Address GSTIN",
			fieldtype="Data",
			insert_after="customer_address",
			read_only=1,
			fetch_from="customer_address.gstin",
			print_hide=1,
			length=15,
		),
		dict(
			fieldname="customer_gstin",
			label="Customer GSTIN",
			fieldtype="Data",
			insert_after="shipping_address_name",
			fetch_from="shipping_address_name.gstin",
			print_hide=1,
			length=15,
		),
		dict(
			fieldname="place_of_supply",
			label="Place of Supply",
			fieldtype="Data",
			insert_after="customer_gstin",
			print_hide=1,
			read_only=1,
			length=50,
		),
		dict(
			fieldname="company_gstin",
			label="Company GSTIN",
			fieldtype="Data",
			insert_after="company_address",
			fetch_from="company_address.gstin",
			print_hide=1,
			read_only=1,
			length=15,
		),
	]

	custom_fields = {"Quotation": sales_invoice_gst_fields}

	create_custom_fields(custom_fields, update=True)
