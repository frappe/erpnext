import frappe

import erpnext

TAX_DOCTYPES = ("Sales Taxes and Charges", "Purchase Taxes and Charges")


def execute():
	rules = frappe.get_all("Shipping Rule", fields=["name", "account", "cost_center", "company"])
	if not rules:
		return

	for doctype in frappe.get_all(
		"DocField", filters={"fieldname": "shipping_rule", "options": "Shipping Rule"}, pluck="parent"
	):
		taxes_field = frappe.get_meta(doctype).get_field("taxes")
		if taxes_field and taxes_field.options in TAX_DOCTYPES:
			for rule in rules:
				flag_shipping_rows(doctype, taxes_field.options, rule)


def flag_shipping_rows(doctype, taxes_doctype, rule):
	# same match the rule used before the flag existed, so older documents keep their behaviour
	parent = frappe.qb.DocType(doctype)
	tax = frappe.qb.DocType(taxes_doctype)
	parents = frappe.qb.from_(parent).select(parent.name).where(parent.shipping_rule == rule.name)

	if rule.cost_center:
		cost_center_match = tax.cost_center == rule.cost_center
	else:
		default_cost_center = erpnext.get_default_cost_center(rule.company) or ""
		cost_center_match = tax.cost_center.isnull() | tax.cost_center.isin(("", default_cost_center))

	frappe.qb.update(tax).set(tax.set_by_shipping_rule, 1).where(
		(tax.parenttype == doctype)
		& tax.parent.isin(parents)
		& (tax.charge_type == "Actual")
		& (tax.account_head == rule.account)
		& cost_center_match
	).run()
