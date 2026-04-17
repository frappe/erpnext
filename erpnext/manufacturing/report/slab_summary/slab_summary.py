# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	filters = filters or {}

	columns = get_columns()
	data = get_data(filters)

	return columns, data


def get_columns():
	return [
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Data",
			"width": 230,
		},
		{
			"label": _("Slabs Planned"),
			"fieldname": "slabs_planned",
			"fieldtype": "Float",
			"width": 180,
			"precision": 1,
		},
		{
			"label": _("Slabs Produced"),
			"fieldname": "slabs_produced",
			"fieldtype": "Float",
			"width": 180,
			"precision": 1,
		},
		{
			"label": _("Slabs In Progress"),
			"fieldname": "slabs_in_progress",
			"fieldtype": "Float",
			"width": 180,
			"precision": 1,
		},
		{
			"label": _("Valuation Rate"),
			"fieldname": "valuation_rate",
			"fieldtype": "Currency",
			"width": 200,
		},
		{
			"label": _("Cost of Production"),
			"fieldname": "cost_of_production",
			"fieldtype": "Currency",
			"width": 225,
		},
	]


def get_data(filters):
	if not filters.get("from_date") or not filters.get("to_date"):
		return []

	ppi_conditions = get_conditions(filters, "ppi")
	sle_conditions = get_conditions(filters, "sle")

	planned_data = frappe.db.sql(
		f"""
		SELECT ppi.item_code, SUM(ppi.planned_qty) as slabs_planned
		FROM `tabProduction Plan Item` ppi
		INNER JOIN `tabProduction Plan` pp ON pp.name = ppi.parent
		WHERE pp.docstatus = 1
			AND pp.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND {ppi_conditions}
		GROUP BY ppi.item_code
	""",
		filters,
		as_dict=1,
	)

	produced_data = frappe.db.sql(
		f"""
		SELECT sle.item_code,
			SUM(sle.actual_qty) as slabs_produced,
			SUM(sle.actual_qty * sle.valuation_rate) as cost_of_production,
			sle.valuation_rate as valuation_rate
		FROM `tabStock Ledger Entry` sle
		WHERE sle.warehouse LIKE '%%Finished Goods Warehouse%%'
			AND sle.actual_qty > 0
			AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND {sle_conditions}
		GROUP BY sle.item_code
	""",
		filters,
		as_dict=1,
	)

	summary = {}

	for row in planned_data:
		item_code = row.item_code
		summary[item_code] = {
			"item_code": item_code,
			"slabs_planned": row.slabs_planned or 0,
			"slabs_produced": 0,
			"slabs_in_progress": 0,
			"valuation_rate": 0,
			"cost_of_production": 0,
		}

	for row in produced_data:
		item_code = row.item_code
		if item_code in summary:
			summary[item_code]["slabs_produced"] = row.slabs_produced or 0
			summary[item_code]["cost_of_production"] = row.cost_of_production or 0
			summary[item_code]["valuation_rate"] = row.valuation_rate or 0
		else:
			summary[item_code] = {
				"item_code": item_code,
				"slabs_planned": 0,
				"slabs_produced": row.slabs_produced or 0,
				"slabs_in_progress": 0,
				"valuation_rate": row.valuation_rate or 0,
				"cost_of_production": row.cost_of_production or 0,
			}

	# 4. Calculate in-progress and prepare result
	result = []
	for row in summary.values():
		in_progress = row["slabs_planned"] - row["slabs_produced"]
		row["slabs_in_progress"] = max(0, in_progress)
		result.append(row)

	return sorted(result, key=lambda x: x["slabs_planned"], reverse=True)


def get_conditions(filters, table_alias):
	conditions = []
	if filters.get("item_code"):
		conditions.append(f"{table_alias}.item_code = %(item_code)s")
	if table_alias == "sle" and not filters.get("item_code"):
		pass
	return " AND ".join(conditions) if conditions else "1=1"
