# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.desk.reportview import build_match_conditions
from frappe.model.meta import get_field_precision
from frappe.query_builder.functions import IfNull, Round
from pypika.terms import Bracket, LiteralValue

from erpnext import get_default_currency


def get_ordered_to_be_billed_data(args, filters=None):
	doctype_name, party = args.get("doctype"), args.get("party")
	child_tab = doctype_name + " Item"
	precision = (
		get_field_precision(
			frappe.get_meta(child_tab).get_field("billed_amt"), currency=get_default_currency()
		)
		or 2
	)

	doctype = frappe.qb.DocType(doctype_name)
	child_doctype = frappe.qb.DocType(child_tab)
	item = frappe.qb.DocType("Item")

	docname = filters.get(args.get("reference_field"), None)
	project_field = get_project_field(doctype, child_doctype, party)

	query = (
		frappe.qb.from_(doctype)
		.inner_join(child_doctype)
		.on(doctype.name == child_doctype.parent)
		.join(item)
		.on(item.name == child_doctype.item_code)
		.select(
			doctype.name,
			doctype[args.get("date")].as_("date"),
			doctype[party],
			doctype[party + "_name"],
			child_doctype.item_code,
			child_doctype.base_amount.as_("amount"),
			(child_doctype.billed_amt * IfNull(doctype.conversion_rate, 1)).as_("billed_amount"),
			(child_doctype.base_rate * IfNull(child_doctype.returned_qty, 0)).as_("returned_amount"),
			(
				child_doctype.base_amount
				- (child_doctype.billed_amt * IfNull(doctype.conversion_rate, 1))
				- (child_doctype.base_rate * IfNull(child_doctype.returned_qty, 0))
			).as_("pending_amount"),
			child_doctype.item_name,
			child_doctype.description,
			project_field,
			doctype.company,
		)
		.where(
			(doctype.docstatus == 1)
			& (doctype.status.notin(["Closed", "Completed"]))
			& (doctype.company == filters.get("company"))
			& (doctype.posting_date <= filters.get("posting_date"))
			& (child_doctype.amount > 0)
			& (item.is_stock_item == 1)
			& (
				child_doctype.base_amount
				- Round(child_doctype.billed_amt * IfNull(doctype.conversion_rate, 1), precision)
				- (child_doctype.base_rate * IfNull(child_doctype.returned_qty, 0))
			)
			> 0
		)
		.orderby(doctype[args.get("order")], order=args.get("order_by"))
	)

	if docname:
		query = query.where(doctype.name == docname)

	if match_conditions := build_match_conditions(doctype_name):
		query = query.where(Bracket(LiteralValue(match_conditions)))

	if condition := get_child_permission_conditions(child_doctype, child_tab):
		query = query.where(condition)

	return query.run(as_dict=True)


def get_child_permission_conditions(child_table, child_doctype_name):
	user_permissions = frappe.permissions.get_user_permissions(frappe.session.user)
	if not user_permissions:
		return None

	strict_user_permissions = frappe.get_system_settings("apply_strict_user_permissions")
	condition = None

	for df in frappe.get_meta(child_doctype_name).get_link_fields():
		if df.get("ignore_user_permissions"):
			continue

		permitted_docs = [
			d.get("doc")
			for d in user_permissions.get(df.get("options"), [])
			if not d.get("applicable_for") or d.get("applicable_for") == child_doctype_name
		]
		if not permitted_docs:
			continue

		field = child_table[df.get("fieldname")]
		field_condition = (
			field.isin(permitted_docs)
			if strict_user_permissions
			else (IfNull(field, "") == "") | field.isin(permitted_docs)
		)
		condition = field_condition if condition is None else condition & field_condition

	return condition


def get_project_field(doctype, child_doctype, party):
	if party == "supplier":
		return child_doctype.project
	return doctype.project
