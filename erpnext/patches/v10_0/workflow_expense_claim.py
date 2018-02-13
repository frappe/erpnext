# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	if frappe.db.a_row_exists("Expense Claim"):
		frappe.reload_doc("hr", "doctype", "expense_claim")
		frappe.reload_doc("hr", "doctype", "vehicle_log")
		frappe.reload_doc("hr", "doctype", "expense_claim_advance")
		frappe.reload_doc("workflow", "doctype", "workflow")

		states = {'Approved': 'Success', 'Rejected': 'Danger', 'Draft': 'Warning'}
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

		if not frappe.db.exists("Workflow", "Expense Approval"):
			frappe.get_doc({
				'doctype': 'Workflow',
				'workflow_name': 'Expense Approval',
				'document_type': 'Expense Claim',
				'is_active': 1,
				'workflow_state_field': 'workflow_state',
				'states': [{
					"state": 'Draft',
					"doc_status": 0,
					"allow_edit": 'Employee'
				}, {
					"state": 'Approved',
					"doc_status": 1,
					"allow_edit": 'Expense Approver'
				}, {
					"state": 'Rejected',
					"doc_status": 0,
					"allow_edit": 'Expense Approver'
				}],
				'transitions': [{
					"state": 'Draft',
					"action": 'Approve',
					"next_state": 'Approved',
					"allowed": 'Expense Approver'
				},
				{
					"state": 'Draft',
					"action": 'Reject',
					"next_state": 'Rejected',
					"allowed": 'Expense Approver'
				}]
			}).insert(ignore_permissions=True)

		if frappe.db.has_column("Expense Claim", "status"):
			frappe.db.sql("""update `tabExpense Claim` set workflow_state = approval_status""")
