# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	if frappe.db.a_row_exists("Leave Application"):
		frappe.reload_doc("hr", "doctype", "leave_application")
		frappe.reload_doc("workflow", "doctype", "workflow")
		states = {'Approved': 'Success', 'Rejected': 'Danger', 'Open': 'Warning'}

		for state, style in states.items():
			if not frappe.db.exists("Workflow State", state):
				frappe.get_doc({
					'doctype': 'Workflow State',
					'workflow_state_name': state,
					'style': style
				}).insert(ignore_permissions=True)

		for action in ['Approve', 'Reject']:
			if not frappe.db.exists("Workflow Action", action):
				frappe.get_doc({
					'doctype': 'Workflow Action',
					'workflow_action_name': action
				}).insert(ignore_permissions=True)

		if not frappe.db.exists("Workflow", "Leave Approval"):
			frappe.get_doc({
				'doctype': 'Workflow',
				'workflow_name': 'Leave Approval',
				'document_type': 'Leave Application',
				'is_active': 1,
				'workflow_state_field': 'workflow_state',
				'states': [{
					"state": 'Open',
					"doc_status": 0,
					"allow_edit": 'Employee'
				}, {
					"state": 'Approved',
					"doc_status": 1,
					"allow_edit": 'Leave Approver'
				}, {
					"state": 'Rejected',
					"doc_status": 0,
					"allow_edit": 'Leave Approver'
				}],
				'transitions': [{
					"state": 'Open',
					"action": 'Approve',
					"next_state": 'Approved',
					"allowed": 'Leave Approver'
				},
				{
					"state": 'Open',
					"action": 'Reject',
					"next_state": 'Rejected',
					"allowed": 'Leave Approver'
				}]
			}).insert(ignore_permissions=True)

		if frappe.db.has_column("Leave Application", "status"):
			frappe.db.sql("""update `tabLeave Application` set workflow_state = status""")

		if frappe.db.has_column("Leave Application", "workflow_state"):
			frappe.db.sql("""update `tabWorkflow Document State` set doc_status = 0 where parent = "Leave Approval" \
			and state = "Rejected" and doc_status = 1""")
			frappe.db.sql("""update `tabLeave Application` set docstatus = 0  where workflow_state = "Rejected" and docstatus = 1""")
