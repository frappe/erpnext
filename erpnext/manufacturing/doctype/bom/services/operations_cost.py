# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Operating-cost helpers applied to Stock Entry / Job Card from a BOM.

Extracted from bom.py; bom.py re-exports them for backward compatibility.
"""

import frappe
from frappe import _
from frappe.query_builder import Field
from frappe.query_builder.functions import IfNull, Sum
from frappe.utils import cint, flt


def add_additional_cost(stock_entry, work_order, job_card=None):
	# Add non stock items cost in the additional cost
	stock_entry.additional_costs = []
	expense_account = frappe.get_value(
		"Company",
		work_order.company,
		"default_operating_cost_account",
	)
	add_non_stock_items_cost(stock_entry, work_order, expense_account, job_card=job_card)
	add_operations_cost(stock_entry, work_order, expense_account, job_card=job_card)


def add_non_stock_items_cost(stock_entry, work_order, expense_account, job_card=None):
	bom = frappe.get_doc("BOM", work_order.bom_no)
	item_amounts = _non_phantom_item_amounts(bom, _bom_items_table(work_order, job_card))
	cost = _non_stock_items_cost(item_amounts, stock_entry, bom)

	if cost:
		stock_entry.append(
			"additional_costs",
			{"expense_account": expense_account, "description": _("Non stock items"), "amount": cost},
		)


def _bom_items_table(work_order, job_card):
	if work_order and not job_card:
		return "exploded_items" if work_order.get("use_multi_level_bom") else "items"
	return "items"


def _non_phantom_item_amounts(bom, table):
	items = frappe._dict()
	for d in bom.get(table):
		# Phantom item is exploded, so its cost is considered via its components
		if d.get("is_phantom_item"):
			continue

		items.setdefault(d.item_code, 0)
		items[d.item_code] += flt(d.amount)
	return items


def _non_stock_items_cost(item_amounts, stock_entry, bom):
	non_stock_items = frappe.get_all(
		"Item",
		fields="name",
		filters=[["name", "in", list(item_amounts.keys())], [IfNull(Field("is_stock_item"), 0), "=", 0]],
		as_list=1,
	)

	cost = 0.0
	for name in non_stock_items:
		cost += flt(item_amounts.get(name[0])) * flt(stock_entry.fg_completed_qty) / flt(bom.quantity)
	return cost


def add_operating_cost_component_wise(stock_entry, work_order=None, op_expense_account=None, job_card=None):
	if not work_order:
		return False

	cost_added = False
	for row in work_order.operations:
		if job_card and job_card.operation_id != row.name:
			continue
		if not row.actual_operation_time:
			continue
		if _add_operation_workstation_costs(stock_entry, work_order, row, op_expense_account):
			cost_added = True

	return cost_added


def _add_operation_workstation_costs(stock_entry, work_order, row, op_expense_account):
	from erpnext.stock.doctype.stock_entry.stock_entry import get_consumed_operating_cost

	workstation_cost = frappe.get_all(
		"Workstation Cost",
		fields=["operating_component", "operating_cost"],
		filters={"parent": row.workstation, "parenttype": "Workstation"},
	)
	consumed = get_consumed_operating_cost(work_order.name, stock_entry.bom_no, row.name) or []

	cost_added = False
	for wc in workstation_cost:
		if _append_workstation_cost(stock_entry, row, wc, consumed, op_expense_account):
			cost_added = True
	return cost_added


def _append_workstation_cost(stock_entry, row, wc, consumed, op_expense_account):
	expense_account = get_component_account(wc.operating_component, stock_entry.company) or op_expense_account
	consumed_op_cost = next(
		(c for c in consumed if c.get("operating_component") == wc.operating_component), {}
	)
	actual = _actual_operating_cost(wc, row, consumed_op_cost)
	if not actual:
		return False

	remaining_qty = row.completed_qty - consumed_op_cost.get("consumed_qty", 0)
	operating_cost = (actual / (remaining_qty or 1)) * stock_entry.fg_completed_qty
	qty = min(remaining_qty, stock_entry.fg_completed_qty)
	row_data = _workstation_cost_row(expense_account, row, wc, actual, operating_cost, qty)
	stock_entry.append("additional_costs", row_data)
	return True


def _actual_operating_cost(wc, row, consumed_op_cost):
	return flt(
		flt(wc.operating_cost) * flt(flt(row.actual_operation_time) / 60.0)
		- flt(consumed_op_cost.get("consumed_cost")),
		row.precision("actual_operating_cost"),
	)


def _workstation_cost_row(expense_account, row, wc, actual, operating_cost, qty):
	precision = frappe.get_precision("Landed Cost Taxes and Charges", "amount")
	return {
		"expense_account": expense_account,
		"description": _("{0} Operating Cost for operation {1}").format(
			wc.operating_component, row.operation
		),
		"amount": flt(min(operating_cost, actual), precision),
		"has_operating_cost": 1,
		"operation_id": row.name,
		"operating_component": wc.operating_component,
		"qty": qty,
	}


@frappe.request_cache
def get_component_account(parent, company):
	return frappe.db.get_value(
		"Workstation Operating Component Account", {"parent": parent, "company": company}, "expense_account"
	)


def add_operations_cost(stock_entry, work_order=None, expense_account=None, job_card=None):
	from erpnext.stock.doctype.stock_entry.stock_entry import get_remaining_operating_cost

	remaining_operating_cost = get_remaining_operating_cost(work_order, stock_entry.bom_no)
	if remaining_operating_cost:
		_add_remaining_operating_cost(
			stock_entry, work_order, expense_account, job_card, remaining_operating_cost
		)

	_add_additional_operating_cost(stock_entry, work_order, expense_account)
	_add_corrective_operation_cost(stock_entry, work_order, expense_account)


def _add_remaining_operating_cost(stock_entry, work_order, expense_account, job_card, remaining_cost):
	if add_operating_cost_component_wise(stock_entry, work_order, expense_account, job_card=job_card):
		return
	if job_card:
		return

	precision = frappe.get_precision("Landed Cost Taxes and Charges", "amount")
	stock_entry.append(
		"additional_costs",
		{
			"expense_account": expense_account,
			"description": _("Operating Cost as per Work Order / BOM"),
			"amount": flt(remaining_cost * stock_entry.fg_completed_qty, precision),
			"has_operating_cost": 1,
		},
	)


def _add_additional_operating_cost(stock_entry, work_order, expense_account):
	if not (work_order and work_order.additional_operating_cost and work_order.qty):
		return

	per_unit = flt(work_order.additional_operating_cost) / flt(work_order.qty)
	if not per_unit:
		return

	stock_entry.append(
		"additional_costs",
		{
			"expense_account": expense_account,
			"description": "Additional Operating Cost",
			"amount": per_unit * flt(stock_entry.fg_completed_qty),
		},
	)


def _add_corrective_operation_cost(stock_entry, work_order, expense_account):
	if not (work_order and work_order.corrective_operation_cost and _corrective_cost_enabled()):
		return

	max_qty = _max_operation_quantity(work_order) - work_order.produced_qty
	remaining = work_order.corrective_operation_cost - _utilised_corrective_cost(work_order)
	stock_entry.append(
		"additional_costs",
		{
			"expense_account": expense_account,
			"description": "Corrective Operation Cost",
			"has_corrective_cost": 1,
			"amount": remaining / max_qty * flt(stock_entry.fg_completed_qty),
		},
	)


def _max_operation_quantity(work_order):
	table = frappe.qb.DocType("Job Card")
	query = (
		frappe.qb.from_(table)
		.select(Sum(table.total_completed_qty).as_("qty"))
		.where(
			(table.docstatus == 1)
			& (table.work_order == work_order.name)
			& (table.is_corrective_job_card == 0)
		)
		.groupby(table.operation)
	)
	return min([d.qty for d in query.run(as_dict=True)], default=0)


def _corrective_cost_enabled():
	return cint(
		frappe.db.get_single_value(
			"Manufacturing Settings", "add_corrective_operation_cost_in_finished_good_valuation"
		)
	)


def _utilised_corrective_cost(work_order):
	charges = frappe.qb.DocType("Landed Cost Taxes and Charges")
	query = (
		frappe.qb.from_(charges)
		.select(Sum(charges.amount).as_("amount"))
		.where(
			charges.parent.isin(_manufacture_stock_entries(work_order)) & (charges.has_corrective_cost == 1)
		)
	)
	return query.run(as_dict=True)[0].amount or 0


def _manufacture_stock_entries(work_order):
	stock_entry = frappe.qb.DocType("Stock Entry")
	return (
		frappe.qb.from_(stock_entry)
		.select(stock_entry.name)
		.where(
			(stock_entry.docstatus == 1)
			& (stock_entry.work_order == work_order.name)
			& (stock_entry.purpose == "Manufacture")
		)
	)


def get_op_cost_from_sub_assemblies(bom_no, op_cost=0):
	# Get operating cost from sub-assemblies

	bom_items = frappe.get_all(
		"BOM Item", filters={"parent": bom_no, "docstatus": 1}, fields=["bom_no"], order_by="idx asc"
	)

	for row in bom_items:
		if not row.bom_no:
			continue

		if cost := frappe.get_cached_value("BOM", row.bom_no, "operating_cost_per_bom_quantity"):
			op_cost += flt(cost)
			get_op_cost_from_sub_assemblies(row.bom_no, op_cost)

	return op_cost


def get_secondary_items_from_sub_assemblies(bom_no, company, qty, secondary_items=None):
	from erpnext.manufacturing.doctype.bom.bom import get_bom_items_as_dict

	if not secondary_items:
		secondary_items = {}

	for row in _child_bom_items_with_qty(bom_no):
		if not row.bom_no:
			continue

		qty = flt(row.qty) * flt(qty)
		items = get_bom_items_as_dict(row.bom_no, company, qty=qty, fetch_exploded=0, fetch_secondary_items=1)
		secondary_items.update(items)
		get_secondary_items_from_sub_assemblies(row.bom_no, company, qty, secondary_items)

	return secondary_items


def _child_bom_items_with_qty(bom_no):
	return frappe.get_all(
		"BOM Item", filters={"parent": bom_no, "docstatus": 1}, fields=["bom_no", "qty"], order_by="idx asc"
	)
