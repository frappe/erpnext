import frappe


def execute():
	from erpnext.setup.setup_wizard.operations.install_fixtures import read_lines

	frappe.reload_doc("selling", "doctype", "sales_partner_type")

	frappe.local.lang = frappe.db.get_default("lang") or "en"

	default_sales_partner_type = read_lines("sales_partner_type.txt")

	for s in default_sales_partner_type:
		insert_sales_partner_type(s)

	# get partner type in existing forms (customized)
	# and create a document if not created
	for d in ["Sales Partner"]:
		partner_type = frappe.db.sql_list(f"select distinct partner_type from `tab{d}`")
		for s in partner_type:
			if s and s not in default_sales_partner_type:
				insert_sales_partner_type(s)

		# remove customization for partner type
		for p in frappe.get_all(
			"Property Setter", {"doc_type": d, "field_name": "partner_type", "property": "options"}
		):
			frappe.delete_doc("Property Setter", p.name)


def insert_sales_partner_type(s):
	if not frappe.db.exists("Sales Partner Type", s):
		frappe.get_doc(dict(doctype="Sales Partner Type", sales_partner_type=s)).insert()
