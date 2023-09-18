import frappe


def execute():
	if frappe.db.table_exists("Scorecard"):
		frappe.reload_doc("Risk", "doctype", "Scorecard")
	elif frappe.db.table_exists("Supplier Scorecard"):
		frappe.rename_doc("DocType", "Supplier Scorecard", "Scorecard", force=True)
		frappe.reload_doc("Risk", "doctype", "Scorecard")

	if frappe.db.table_exists("Scorecard Scoring Criteria"):
		frappe.reload_doc("Risk", "doctype", "Scorecard Scoring Criteria")
	elif frappe.db.table_exists("Supplier Scorecard Scoring Criteria"):
		frappe.rename_doc(
			"DocType", "Supplier Scorecard Scoring Criteria", "Scorecard Scoring Criteria", force=True
		)
		frappe.reload_doc("Risk", "doctype", "Scorecard Scoring Criteria")

	if frappe.db.table_exists("Scorecard Criteria"):
		frappe.reload_doc("Risk", "doctype", "Scorecard Criteria")
	elif frappe.db.table_exists("Supplier Scorecard Criteria"):
		frappe.rename_doc("DocType", "Supplier Scorecard Criteria", "Scorecard Criteria", force=True)
		frappe.reload_doc("Risk", "doctype", "Scorecard Criteria")

	if frappe.db.table_exists("Scorecard Scoring Standing"):
		frappe.reload_doc("Risk", "doctype", "Scorecard Scoring Standing")
	elif frappe.db.table_exists("Supplier Scorecard Scoring Standing"):
		frappe.rename_doc(
			"DocType", "Supplier Scorecard Scoring Standing", "Scorecard Scoring Standing", force=True
		)
		frappe.reload_doc("Risk", "doctype", "Scorecard Scoring Standing")

	if frappe.db.table_exists("Scorecard Standing"):
		frappe.reload_doc("Risk", "doctype", "Scorecard Standing")
	elif frappe.db.table_exists("Supplier Scorecard Standing"):
		frappe.rename_doc("DocType", "Supplier Scorecard Standing", "Scorecard Standing", force=True)
		frappe.reload_doc("Risk", "doctype", "Scorecard Standing")

	if frappe.db.table_exists("Scorecard Scoring Variable"):
		frappe.reload_doc("Risk", "doctype", "Scorecard Scoring Variable")
	elif frappe.db.table_exists("Supplier Scorecard Scoring Variable"):
		frappe.rename_doc(
			"DocType", "Supplier Scorecard Scoring Variable", "Scorecard Scoring Variable", force=True
		)
		frappe.reload_doc("Risk", "doctype", "Scorecard Scoring Variable")

	if frappe.db.table_exists("Scorecard Variable"):
		frappe.reload_doc("Risk", "doctype", "Scorecard Variable")
	elif frappe.db.table_exists("Supplier Scorecard Variable"):
		frappe.rename_doc("DocType", "Supplier Scorecard Variable", "Scorecard Variable", force=True)
		frappe.reload_doc("Risk", "doctype", "Scorecard Variable")

	if frappe.db.table_exists("Scorecard Period"):
		frappe.reload_doc("Risk", "doctype", "Scorecard Period")
	elif frappe.db.table_exists("Supplier Scorecard Period"):
		frappe.rename_doc("DocType", "Supplier Scorecard Period", "Scorecard Period", force=True)
		frappe.reload_doc("Risk", "doctype", "Scorecard Period")
