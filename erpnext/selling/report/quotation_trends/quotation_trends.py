# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from frappe import _

from erpnext.controllers.trends import get_columns, get_data


def execute(filters=None):
	if not filters:
		filters = {}
	data = []
	conditions = get_columns(filters, "Quotation")
	data = get_data(filters, conditions)

	chart_data = get_chart_data(data, conditions, filters)

	return conditions["columns"], data, None, chart_data


def get_chart_data(data, conditions, filters):
	if not (data and conditions):
		return []

	datapoints = []

	if filters.get("based_on") in ["Customer"]:
		start = 3
	elif filters.get("based_on") in ["Item"]:
		start = 2
	else:
		start = 1

	if filters.get("group_by"):
		start += 1

	# fetch only periodic columns as labels
	columns = conditions.get("columns")[start:-2][2::2]
	labels = [column.split(":")[0] for column in columns]
	datapoints = [0] * len(labels)

	group_by_col_idx = None
	if filters.get("group_by"):
		group_by_col_idx = conditions["columns"].index(conditions["grbc"][0])

	for row in data:
		# Skip the final grand-total row
		if row[0] == f"'{_('Total')}'":
			continue
		if group_by_col_idx is not None and row[group_by_col_idx] == "":
			continue
		# Remove None values and compute only periodic data
		row = [x if x else 0 for x in row[start:-2]]
		row = row[2::2]

		for i in range(len(row)):
			datapoints[i] += row[i]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _(filters.get("period")) + " " + _("Quoted Amount"), "values": datapoints}],
		},
		"type": "line",
		"lineOptions": {"regionFill": 1},
		"fieldtype": "Currency",
		"options": "currency",
		"currency": conditions.get("company_currency"),
	}
