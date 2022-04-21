import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	company = frappe.get_all("Company", filters={"country": "India"}, fields=["name"])
	if not company:
		return

	hsn_sac_field = dict(
		fieldname="gst_hsn_code",
		label="HSN/SAC",
		fieldtype="Data",
		fetch_from="item_code.gst_hsn_code",
		insert_after="description",
		allow_on_submit=1,
		print_hide=1,
		fetch_if_empty=1,
	)
	nil_rated_exempt = dict(
		fieldname="is_nil_exempt",
		label="Is Nil Rated or Exempted",
		fieldtype="Check",
		fetch_from="item_code.is_nil_exempt",
		insert_after="gst_hsn_code",
		print_hide=1,
	)
	is_non_gst = dict(
		fieldname="is_non_gst",
		label="Is Non GST",
		fieldtype="Check",
		fetch_from="item_code.is_non_gst",
		insert_after="is_nil_exempt",
		print_hide=1,
	)
	taxable_value = dict(
		fieldname="taxable_value",
		label="Taxable Value",
		fieldtype="Currency",
		insert_after="base_net_amount",
		hidden=1,
		options="Company:company:default_currency",
		print_hide=1,
	)
	sales_invoice_gst_fields = [
		dict(
			fieldname="billing_address_gstin",
			label="Billing Address GSTIN",
			fieldtype="Data",
			insert_after="customer_address",
			read_only=1,
			fetch_from="customer_address.gstin",
			print_hide=1,
		),
		dict(
			fieldname="customer_gstin",
			label="Customer GSTIN",
			fieldtype="Data",
			insert_after="shipping_address_name",
			fetch_from="shipping_address_name.gstin",
			print_hide=1,
		),
		dict(
			fieldname="place_of_supply",
			label="Place of Supply",
			fieldtype="Data",
			insert_after="customer_gstin",
			print_hide=1,
			read_only=1,
		),
		dict(
			fieldname="company_gstin",
			label="Company GSTIN",
			fieldtype="Data",
			insert_after="company_address",
			fetch_from="company_address.gstin",
			print_hide=1,
			read_only=1,
		),
	]

	custom_fields = {
		"POS Invoice": sales_invoice_gst_fields,
		"POS Invoice Item": [hsn_sac_field, nil_rated_exempt, is_non_gst, taxable_value],
	}

	create_custom_fields(custom_fields, update=True)
