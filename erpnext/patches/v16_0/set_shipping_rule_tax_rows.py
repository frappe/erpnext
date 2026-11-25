import frappe
from frappe.query_builder.functions import IfNull
from frappe.utils import create_batch

TAX_DOCTYPES = ("Sales Taxes and Charges", "Purchase Taxes and Charges")


def execute():
	for doctype in frappe.get_all(
		"DocField", filters={"fieldname": "shipping_rule", "options": "Shipping Rule"}, pluck="parent"
	):
		taxes_field = frappe.get_meta(doctype).get_field("taxes")
		if taxes_field and taxes_field.options in TAX_DOCTYPES:
			rows = get_matching_rows(doctype, taxes_field.options)
			tag_rows(taxes_field.options, pick_shipping_rows(rows))


def get_matching_rows(doctype, taxes_doctype):
	"""Rows the shipping rule matched before the tag existed: Actual, on its account and cost center."""
	parent = frappe.qb.DocType(doctype)
	tax = frappe.qb.DocType(taxes_doctype)
	rule = frappe.qb.DocType("Shipping Rule")
	company = frappe.qb.DocType("Company")

	rule_has_cost_center = IfNull(rule.cost_center, "") != ""
	cost_center_match = (rule_has_cost_center & (tax.cost_center == rule.cost_center)) | (
		~rule_has_cost_center
		& ((IfNull(tax.cost_center, "") == "") | (tax.cost_center == company.cost_center))
	)

	return (
		frappe.qb.from_(tax)
		.join(parent)
		.on(tax.parent == parent.name)
		.join(rule)
		.on(rule.name == parent.shipping_rule)
		.left_join(company)
		.on(company.name == parent.company)
		.select(tax.name, tax.parent, tax.idx, tax.description, rule.label)
		.where(
			(tax.parenttype == doctype)
			& (tax.parentfield == "taxes")
			& (tax.charge_type == "Actual")
			& (tax.account_head == rule.account)
			& cost_center_match
		)
		.run(as_dict=True)
	)


def pick_shipping_rows(rows):
	# one row per document: the one with the rule's label, else the last match the rule used to update
	picked = {}
	for row in sorted(rows, key=lambda row: (row.description == row.label, row.idx)):
		picked[row.parent] = row.name

	return list(picked.values())


def tag_rows(taxes_doctype, names):
	tax = frappe.qb.DocType(taxes_doctype)
	for batch in create_batch(names, 1000):
		frappe.qb.update(tax).set(tax.set_by_shipping_rule, 1).where(tax.name.isin(batch)).run()
