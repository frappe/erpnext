import frappe
from frappe import _


def execute(filters=None):
	return get_columns(), get_data()


def get_columns():
	return [
		{
			"label": _("Name"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Quality Action",
			"width": 200,
		},
		{"label": _("Action"), "fieldname": "corrective_preventive", "fieldtype": "Data", "width": 200},
		{
			"label": _("Review"),
			"fieldname": "review",
			"fieldtype": "Link",
			"options": "Quality Review",
			"width": 200,
		},
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 120},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 150},
	]


def get_data():
	return frappe.get_list(
		"Quality Action",
		filters={"review": ["is", "set"]},
		fields=["name", "corrective_preventive", "review", "date", "status"],
	)
