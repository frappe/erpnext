import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field


def execute():
	"Add Field Filters, that are not standard fields in Website Item, as Custom Fields."
	settings = frappe.get_doc("E Commerce Settings")

	if not (settings.filter_fields or settings.field_filters):
		return

	item_meta = frappe.get_meta("Item")
	valid_item_fields = [
		df.fieldname for df in item_meta.fields if df.fieldtype in ["Link", "Table MultiSelect"]
	]

	web_item_meta = frappe.get_meta("Website Item")
	valid_web_item_fields = [
		df.fieldname for df in web_item_meta.fields if df.fieldtype in ["Link", "Table MultiSelect"]
	]

	for row in settings.filter_fields:
		# skip if illegal field
		if row.fieldname not in valid_item_fields:
			continue

		# if Item field is not in Website Item, add it as a custom field
		if row.fieldname not in valid_web_item_fields:
			df = item_meta.get_field(row.fieldname)
			create_custom_field(
				"Website Item",
				dict(
					owner="Administrator",
					fieldname=df.fieldname,
					label=df.label,
					fieldtype=df.fieldtype,
					options=df.options,
					description=df.description,
					read_only=df.read_only,
					no_copy=df.no_copy,
					insert_after="on_backorder",
				),
			)

			# map field values
			frappe.db.sql(
				"""
				UPDATE `tabWebsite Item` wi, `tabItem` i
				SET wi.{0} = i.{0}
				WHERE wi.item_code = i.item_code
			""".format(
					row.fieldname
				)
			)
