import frappe
from frappe.utils import cint


def execute():
	frappe.reload_doc("e_commerce", "doctype", "e_commerce_settings")
	frappe.reload_doc("portal", "doctype", "website_filter_field")
	frappe.reload_doc("portal", "doctype", "website_attribute")

	products_settings_fields = [
		"hide_variants",
		"products_per_page",
		"enable_attribute_filters",
		"enable_field_filters",
	]

	shopping_cart_settings_fields = [
		"enabled",
		"show_attachments",
		"show_price",
		"show_stock_availability",
		"enable_variants",
		"show_contact_us_button",
		"show_quantity_in_website",
		"show_apply_coupon_code_in_website",
		"allow_items_not_in_stock",
		"company",
		"price_list",
		"default_customer_group",
		"quotation_series",
		"enable_checkout",
		"payment_success_url",
		"payment_gateway_account",
		"save_quotations_as_draft",
	]

	settings = frappe.get_doc("E Commerce Settings")

	def map_into_e_commerce_settings(doctype, fields):
		singles = frappe.qb.DocType("Singles")
		query = (
			frappe.qb.from_(singles)
			.select(singles["field"], singles.value)
			.where((singles.doctype == doctype) & (singles["field"].isin(fields)))
		)
		data = query.run(as_dict=True)

		# {'enable_attribute_filters': '1', ...}
		mapper = {row.field: row.value for row in data}

		for key, value in mapper.items():
			value = cint(value) if (value and value.isdigit()) else value
			settings.update({key: value})

		settings.save()

	# shift data to E Commerce Settings
	map_into_e_commerce_settings("Products Settings", products_settings_fields)
	map_into_e_commerce_settings("Shopping Cart Settings", shopping_cart_settings_fields)

	# move filters and attributes tables to E Commerce Settings from Products Settings
	for doctype in ("Website Filter Field", "Website Attribute"):
		frappe.db.set_value(
			doctype,
			{"parent": "Products Settings"},
			{"parenttype": "E Commerce Settings", "parent": "E Commerce Settings"},
			update_modified=False,
		)
