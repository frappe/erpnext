import frappe

RENAMED_FIELDS = {
	"first_name": "italy_customer_first_name",
	"last_name": "italy_customer_last_name",
}


def execute():
	"""Rename Italy's Customer name fields, which clash with the standard quick-entry
	first_name/last_name fields, and restore any Italy custom field columns that a
	previously interrupted fixture run left missing."""
	if not has_italy_fixtures():
		return

	duplicate_fieldnames = [
		fieldname for fieldname in RENAMED_FIELDS if frappe.db.exists("Custom Field", f"Customer-{fieldname}")
	]

	from erpnext.regional.italy.setup import get_custom_fields, make_custom_fields

	make_custom_fields()
	for doctype in get_custom_fields():
		frappe.clear_cache(doctype=doctype)
		frappe.db.updatedb(doctype)

	for old_fieldname, new_fieldname in RENAMED_FIELDS.items():
		copy_customer_names(old_fieldname, new_fieldname)

	for old_fieldname in duplicate_fieldnames:
		frappe.delete_doc("Custom Field", f"Customer-{old_fieldname}", force=True)

	if duplicate_fieldnames:
		frappe.clear_cache(doctype="Customer")


def has_italy_fixtures():
	return bool(
		frappe.db.exists("Company", {"country": "Italy"})
		or frappe.db.exists("Custom Field", "Company-fiscal_regime")
	)


def copy_customer_names(old_fieldname, new_fieldname):
	customer = frappe.qb.DocType("Customer")
	old_column = customer[old_fieldname]
	new_column = customer[new_fieldname]
	(
		frappe.qb.update(customer)
		.set(new_column, old_column)
		.where(old_column.isnotnull() & (old_column != ""))
		.where(new_column.isnull() | (new_column == ""))
	).run()
