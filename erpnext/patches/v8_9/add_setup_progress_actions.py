
from __future__ import unicode_literals
import frappe
from frappe import _

def execute():
	"""Add setup progress actions"""
	if not frappe.db.exists('DocType', 'Setup Progress') or not frappe.db.exists('DocType', 'Setup Progress Action'):
		return

	frappe.reload_doc("setup", "doctype", "setup_progress")
	frappe.reload_doc("setup", "doctype", "setup_progress_action")

	actions = [
		{"action_name": "Add Company", "action_doctype": "Company", "min_doc_count": 1, "is_completed": 1,
			"domains": '[]' },
		{"action_name": "Set Sales Target", "action_doctype": "Company", "min_doc_count": 99,
			"action_document": frappe.defaults.get_defaults().get("company") or '',
			"action_field": "monthly_sales_target", "is_completed": 0,
			"domains": '["Manufacturing", "Services", "Retail", "Distribution"]' },
		{"action_name": "Add Customers", "action_doctype": "Customer", "min_doc_count": 1, "is_completed": 0,
			"domains": '["Manufacturing", "Services", "Retail", "Distribution"]' },
		{"action_name": "Add Suppliers", "action_doctype": "Supplier", "min_doc_count": 1, "is_completed": 0,
			"domains": '["Manufacturing", "Services", "Retail", "Distribution"]' },
		{"action_name": "Add Products", "action_doctype": "Item", "min_doc_count": 1, "is_completed": 0,
			"domains": '["Manufacturing", "Services", "Retail", "Distribution"]' },
		{"action_name": "Add Programs", "action_doctype": "Program", "min_doc_count": 1, "is_completed": 0,
			"domains": '["Education"]' },
		{"action_name": "Add Instructors", "action_doctype": "Instructor", "min_doc_count": 1, "is_completed": 0,
			"domains": '["Education"]' },
		{"action_name": "Add Courses", "action_doctype": "Course", "min_doc_count": 1, "is_completed": 0,
			"domains": '["Education"]' },
		{"action_name": "Add Rooms", "action_doctype": "Room", "min_doc_count": 1, "is_completed": 0,
			"domains": '["Education"]' },
		{"action_name": "Add Users", "action_doctype": "User", "min_doc_count": 4, "is_completed": 0,
			"domains": '[]' },
		{"action_name": "Add Letterhead", "action_doctype": "Letter Head", "min_doc_count": 1, "is_completed": 0,
			"domains": '[]' }
	]

	setup_progress = frappe.get_doc("Setup Progress", "Setup Progress")
	setup_progress.actions = []
	for action in actions:
		setup_progress.append("actions", action)

	setup_progress.save(ignore_permissions=True)

