# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	frappe.reload_doc("hr", "doctype", "expense_claim")
	frappe.reload_doc("workflow", "doctype", "workflow")

	doc = frappe.get_doc({
		'doctype': 'Workflow State',
		'workflow_state_name': 'Draft',
		'style': 'Warning'
		}).insert(ignore_permissions=True)

	doc = frappe.get_doc({
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
			"doc_status": 1,
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

	frappe.db.sql("""update `tabExpense Claim` set workflow_state = approval_status""")
	# frappe.db.sql("""alter table `tabExpense Claim` drop column approval_status""")
