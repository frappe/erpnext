import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field


def execute():
	"Add Field Filters, that are not standard fields in Website Item, as Custom Fields."

	def move_table_multiselect_data(docfield):
		"Copy child table data (Table Multiselect) from Item to Website Item for a docfield."
		table_multiselect_data = get_table_multiselect_data(docfield)
		field = docfield.fieldname

		for row in table_multiselect_data:
			# add copied multiselect data rows in Website Item
			web_item = frappe.db.get_value("Website Item", {"item_code": row.parent})
			web_item_doc = frappe.get_doc("Website Item", web_item)

			child_doc = frappe.new_doc(docfield.options, web_item_doc, field)

			for field in ["name", "creation", "modified", "idx"]:
				row[field] = None

			child_doc.update(row)

			child_doc.parenttype = "Website Item"
			child_doc.parent = web_item

			child_doc.insert()

	def get_table_multiselect_data(docfield):
		child_table = frappe.qb.DocType(docfield.options)
		item = frappe.qb.DocType("Item")

		table_multiselect_data = (  # query table data for field
			frappe.qb.from_(child_table)
			.join(item)
			.on(item.item_code == child_table.parent)
			.select(child_table.star)
			.where((child_table.parentfield == docfield.fieldname) & (item.published_in_website == 1))
		).run(as_dict=True)

		return table_multiselect_data

	settings = frappe.get_doc("E Commerce Settings")

	if not (settings.enable_field_filters or settings.filter_fields):
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
			if df.fieldtype == "Table MultiSelect":
				move_table_multiselect_data(df)
			else:
				frappe.db.sql(  # nosemgrep
					"""
						UPDATE `tabWebsite Item` wi, `tabItem` i
						SET wi.{0} = i.{0}
						WHERE wi.item_code = i.item_code
					""".format(
						row.fieldname
					)
				)
