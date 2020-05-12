# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
import json


def get_data():
	return frappe._dict({
		"dashboards": get_dashboards(),
		"charts": get_charts(),
		"number_cards": get_number_cards(),
	})

def get_dashboards():
	return [{
		"name": "<name>",
		"dashboard_name": "<name>",
		"charts": [
			{ "chart": <chart-name> }
		]
	}]

def get_charts():
	return [ { ... } ]

def get_number_cards():
	return [ { ... } ]