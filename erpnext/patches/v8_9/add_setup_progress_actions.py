
from __future__ import unicode_literals
import frappe
from frappe import _

def execute():
	"""Add setup progress actions"""
	frappe.reload_doc("setup", "doctype", "setup_progress")
	frappe.reload_doc("setup", "doctype", "setup_progress_action")

	actions = [
		{"action_name": _("Add Company"), "action_doctype": "Company", "min_doc_count": 1, "is_completed": 1,
			"domains": '[]' },
		{"action_name": _("Set Sales Target"), "action_doctype": "Company", "min_doc_count": 99,
			"action_document": frappe.defaults.get_defaults().get("company") or '',
			"action_field": "monthly_sales_target", "is_completed": 0,
			"domains": '["Manufacturing", "Services", "Retail", "Distribution"]' },
		{"action_name": _("Add Customers"), "action_doctype": "Customer", "min_doc_count": 1, "is_completed": 0,
			"domains": '["Manufacturing", "Services", "Retail", "Distribution"]' },
		{"action_name": _("Add Suppliers"), "action_doctype": "Supplier", "min_doc_count": 1, "is_completed": 0,
			"domains": '["Manufacturing", "Services", "Retail", "Distribution"]' },
		{"action_name": _("Add Products"), "action_doctype": "Item", "min_doc_count": 1, "is_completed": 0,
			"domains": '["Manufacturing", "Services", "Retail", "Distribution"]' },
		{"action_name": _("Add Programs"), "action_doctype": "Program", "min_doc_count": 1, "is_completed": 0,
			"domains": '["Education"]' },
		{"action_name": _("Add Instructors"), "action_doctype": "Instructor", "min_doc_count": 1, "is_completed": 0,
			"domains": '["Education"]' },
		{"action_name": _("Add Courses"), "action_doctype": "Course", "min_doc_count": 1, "is_completed": 0,
			"domains": '["Education"]' },
		{"action_name": _("Add Rooms"), "action_doctype": "Room", "min_doc_count": 1, "is_completed": 0,
			"domains": '["Education"]' },
		{"action_name": _("Add Users"), "action_doctype": "User", "min_doc_count": 4, "is_completed": 0,
			"domains": '[]' }
	]

	setup_progress = frappe.get_doc("Setup Progress", "Setup Progress")
	setup_progress.actions = []
	for action in actions:
		setup_progress.append("actions", action)

	setup_progress.save(ignore_permissions=True)

