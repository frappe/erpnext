# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.workflow import apply_workflow
from frappe.utils import parse_json, today, date_diff


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"label": _("Company"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 180,
		},
		{
			"label": _("DocType"),
			"fieldname": "reference_doctype",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("Document"),
			"fieldname": "reference_name",
			"fieldtype": "Dynamic Link",
			"options": "reference_doctype",
			"width": 200,
		},
		{
			"label": _("Status"),
			"fieldname": "workflow_state",
			"fieldtype": "Data",
			"width": 250,
		},
		{
			"label": _("Created Date"),
			"fieldname": "created_date",
			"fieldtype": "Date",
			"width": 130,
		},
		{
			"label": _("Workflow Date"),
			"fieldname": "workflow_date",
			"fieldtype": "Date",
			"width": 130,
		},
		{
			"label": _("Days Pending"),
			"fieldname": "days_pending",
			"fieldtype": "Int",
			"width": 120,
		},
	]


def get_data(filters):
	user = filters.get("user") or frappe.session.user
	user_roles = frappe.get_roles(user)
	
	workflow_actions = frappe.get_all(
		"Workflow Action",
		filters={
			"status": "Open",
			"role": ["in", user_roles]
		},
		fields=[
			"reference_doctype",
			"reference_name",
			"creation as workflow_date"
		]
	)

	latest_actions = {}

	for wa in workflow_actions:
		key = (wa.reference_doctype, wa.reference_name)

		if key not in latest_actions:
			latest_actions[key] = wa

	workflow_actions = list(latest_actions.values())

	data = []

	for wa in workflow_actions:
		if filters.get("reference_doctype") and wa.reference_doctype != filters.get("reference_doctype"):
			continue

		Doc = frappe.qb.DocType(wa.reference_doctype)

		query = (
			frappe.qb.from_(Doc)
			.select(
				Doc.name,
				Doc.company,
				Doc.workflow_state,
				Doc.creation.as_("created_date"),
			)
			.where(Doc.name == wa.reference_name)
			.where(Doc.docstatus < 2)
		)

		if filters.get("company"):
			query = query.where(Doc.company == filters.get("company"))

		if filters.get("from_date"):
			query = query.where(Doc.creation >= filters.get("from_date"))

		if filters.get("to_date"):
			query = query.where(Doc.creation <= filters.get("to_date"))

		if filters.get("workflow_state"):
			query = query.where(Doc.workflow_state == filters.get("workflow_state"))

		results = query.run(as_dict=True)
		if not results:
			continue

		result = results[0]
		workflow_state = result.get("workflow_state")
		workflow_action = filters.get("workflow_action")
		
		if not workflow_action_allowed(
			wa.reference_doctype,
			workflow_state,
			workflow_action,
			user_roles
		):
			continue

		data.append(
			{
				"company": result.get("company"),
				"reference_doctype": wa.reference_doctype,
				"reference_name": wa.reference_name,
				"workflow_state": workflow_state,
				"created_date": result.get("created_date"),
				"workflow_date": wa.workflow_date,
				"days_pending": date_diff(today(), wa.workflow_date)
			}
		)
	
	data = sorted(data, key=lambda x: x.get("workflow_date") or "", reverse=True)
	return data


def workflow_action_allowed(doctype, workflow_state, workflow_action, user_roles):
	workflow_name = frappe.get_value(
		"Workflow",
		{"document_type": doctype, "is_active": 1},
		"name"
	)

	if not workflow_name:
		return False

	return frappe.db.exists(
		"Workflow Transition",
		{
			"parent": workflow_name,
			"state": workflow_state,
			"action": workflow_action,
			"allowed": ["in", user_roles],
		}
	)


@frappe.whitelist()
def apply_workflow_action(rows, action):
	if isinstance(rows, str):
		rows = parse_json(rows)

	for row in rows:
		doc = frappe.get_doc(row["doctype"], row["name"])

		try:
			apply_workflow(doc, action)
		except Exception:
			frappe.throw(
				_("You do not have permission to perform {0} action on selected document(s).")
				.format(action)
			)