# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate
from erpnext.budget.doctype.budget_amendment.budget_amendment import update_original_budget

class TestBudgetAmendment(FrappeTestCase):
	def setUp(self):
		self.create_missing_records()

	def create_missing_records(self):
		project_name = "_Test Project"
		project = frappe.db.exists("Project", {"project_name": project_name})

		if not project:
			self.project = frappe.get_doc({
				"doctype": "Project",
				"project_name": project_name,
				"company": "_Test Company",
				"status": "Open"
			}).insert(ignore_permissions=True)
		else:
			self.project = frappe.get_doc("Project", project)

		if not frappe.db.exists("Work Breakdown Structure", "TEST-WBS-001"):
			self.wbs = frappe.get_doc({
				"doctype": "Work Breakdown Structure",
				"name": "TEST-WBS-001",
				"project": "PROJ-0016",
				"wbs_name": "Test WBS",
				"overall_budget": 1000,
				"assigned_overall_budget": 200,
				"available_budget": 800,
				"locked": 0
			}).insert(ignore_permissions=True)
		else:
			self.wbs = frappe.get_doc("Work Breakdown Structure", "TEST-WBS-001")

		self.budget_amendment = frappe.get_doc({
			"doctype": "Budget Amendment",
			"company": "_Test Company",
			"posting_date": nowdate(),
			"budget_amendment_items": [{
				"wbs_element": self.wbs.name,
				"level": 1,
				"increment_budget": 500
			}]
		}).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.rollback()

	def test_submit_updates_wbs_budget(self):
		original_budget = self.wbs.overall_budget

		self.budget_amendment.submit()
		self.wbs.reload()

		self.assertEqual(self.wbs.overall_budget, original_budget + 500)
		self.assertEqual(self.wbs.available_budget, self.wbs.overall_budget - self.wbs.assigned_overall_budget)

	def test_cancel_reverses_wbs_budget(self):
		self.budget_amendment.submit()
		self.wbs.reload()
		increased_budget = self.wbs.overall_budget

		self.budget_amendment.cancel()
		self.wbs.reload()

		self.assertEqual(self.wbs.overall_budget, increased_budget - 500)

	def test_budget_entry_created_on_submit(self):
		self.budget_amendment.submit()
		entry = frappe.db.exists("Budget Entry", {"voucher_no": self.budget_amendment.name})
		self.assertTrue(entry, "Budget Entry not created after submission")

