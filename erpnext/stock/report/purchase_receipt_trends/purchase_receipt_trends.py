# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.controllers.trends	import get_columns,get_data

def execute(filters=None):
	if not filters: filters ={}
	data = []
	conditions = get_columns(filters, "Purchase Receipt")
	data = get_data(filters, conditions)

	chart_data = get_chart_data(data)

	return conditions["columns"], data, None, chart_data

def get_chart_data(data):
	labels, datapoints = [], []

	if len(data) > 10:
		data = sorted(data, key = lambda i: i[-1],reverse=True)
		data = data[:10]

	for row in data:
		labels.append(row[0])
		datapoints.append(row[-1])

	return {
		"data": {
			"labels" : labels,
			"datasets" : [
				{
				"name": _("Total Expenditure"),
				"values": datapoints
				}
			]
		},
		"type" : "bar",
		"colors":["#5e64ff"]
	}