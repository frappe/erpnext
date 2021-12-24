# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

from frappe import _

from erpnext.controllers.trends import get_columns, get_data


def execute(filters=None):
	if not filters: filters ={}
	data = []
	conditions = get_columns(filters, "Purchase Order")
	data = get_data(filters, conditions)
	chart_data = get_chart_data(data, conditions, filters)

	return conditions["columns"], data, None, chart_data

def get_chart_data(data, conditions, filters):
	if not (data and conditions):
		return []

	datapoints = []

	start = 2 if filters.get("based_on") in ["Item", "Supplier"] else 1
	if filters.get("group_by"):
		start += 1

	# fetch only periodic columns as labels
	columns = conditions.get("columns")[start:-2][1::2]
	labels = [column.split(':')[0] for column in columns]
	datapoints = [0] * len(labels)

	for row in data:
		# If group by filter, don't add first row of group (it's already summed)
		if not row[start-1]:
			continue
		# Remove None values and compute only periodic data
		row = [x if x else 0 for x in row[start:-2]]
		row  = row[1::2]

		for i in range(len(row)):
			datapoints[i] += row[i]

	return {
		"data" : {
			"labels" : labels,
			"datasets" : [
				{
					"name" : _("{0}").format(filters.get("period")) + _(" Purchase Value"),
					"values" : datapoints
				}
			]
		},
		"type" : "line",
		"lineOptions": {
			"regionFill": 1
		}
	}
