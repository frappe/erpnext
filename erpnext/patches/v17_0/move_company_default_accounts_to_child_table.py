import frappe

from erpnext.accounts.default_accounts import get_purposes


def execute():
	"""Copy the default account columns of Company into rows of `default_accounts`, then drop the columns."""
	columns = set(frappe.db.get_table_columns("Company"))
	company_meta_fields = set(frappe.get_meta("Company", cached=False).get_fieldnames_with_value())
	# a purpose of another app can still be a custom field, keep that column
	purposes = [
		purpose
		for purpose in get_purposes().values()
		if purpose.fieldname in columns and purpose.fieldname not in company_meta_fields
	]
	if not purposes:
		return

	fieldnames = [purpose.fieldname for purpose in purposes]
	companies = frappe.qb.from_("Company").select("name", *fieldnames).run(as_dict=True)
	for company in companies:
		existing_purposes = set(
			frappe.get_all(
				"Company Default Account",
				filters={"parenttype": "Company", "parentfield": "default_accounts", "parent": company.name},
				pluck="purpose",
			)
		)
		idx = len(existing_purposes)
		for purpose in purposes:
			account = company[purpose.fieldname]
			if not account or purpose.key in existing_purposes:
				continue

			idx += 1
			frappe.get_doc(
				{
					"doctype": "Company Default Account",
					"parenttype": "Company",
					"parentfield": "default_accounts",
					"parent": company.name,
					"purpose": purpose.key,
					"account": account,
					"idx": idx,
				}
			).db_insert()

	frappe.db.drop_columns("Company", fieldnames)
	frappe.client_cache.delete_value("table_columns::tabCompany")
	frappe.clear_cache(doctype="Company")
