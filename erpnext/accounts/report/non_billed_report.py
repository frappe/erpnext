# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.meta import get_field_precision

from erpnext import get_default_currency


def get_ordered_to_be_billed_data(args):
	doctype, party = args.get("doctype"), args.get("party")
	child_tab = doctype + " Item"
	precision = (
		get_field_precision(
			frappe.get_meta(child_tab).get_field("billed_amt"), currency=get_default_currency()
		)
		or 2
	)

	project_field = get_project_field(doctype, party)

	return frappe.db.sql(
		"""
		Select
			`{parent_tab}`.name, `{parent_tab}`.{date_field},
			`{parent_tab}`.{party}, `{parent_tab}`.{party}_name,
			`{child_tab}`.item_code,
			`{child_tab}`.base_amount,
			(`{child_tab}`.billed_amt * ifnull(`{parent_tab}`.conversion_rate, 1)),
			(`{child_tab}`.base_rate * ifnull(`{child_tab}`.returned_qty, 0)),
			(`{child_tab}`.base_amount -
			(`{child_tab}`.billed_amt * ifnull(`{parent_tab}`.conversion_rate, 1)) -
			(`{child_tab}`.base_rate * ifnull(`{child_tab}`.returned_qty, 0))),
			`{child_tab}`.item_name, `{child_tab}`.description,
			{project_field}, `{parent_tab}`.company
		from
			`{parent_tab}`, `{child_tab}`
		where
			`{parent_tab}`.name = `{child_tab}`.parent and `{parent_tab}`.docstatus = 1
			and `{parent_tab}`.status not in ('Closed', 'Completed')
			and `{child_tab}`.amount > 0
			and (`{child_tab}`.base_amount -
			round(`{child_tab}`.billed_amt * ifnull(`{parent_tab}`.conversion_rate, 1), {precision}) -
			(`{child_tab}`.base_rate * ifnull(`{child_tab}`.returned_qty, 0))) > 0
		order by
			`{parent_tab}`.{order} {order_by}
		""".format(
			parent_tab="tab" + doctype,
			child_tab="tab" + child_tab,
			precision=precision,
			party=party,
			date_field=args.get("date"),
			project_field=project_field,
			order=args.get("order"),
			order_by=args.get("order_by"),
		)
	)


def get_project_field(doctype, party):
	if party == "supplier":
		doctype = doctype + " Item"
	return "`tab%s`.project" % (doctype)
