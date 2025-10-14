# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import frappe
from frappe.tests.utils import FrappeTestCase


class TestWBSMonthlyDistribution(FrappeTestCase):
	def setUp(self):
		from erpnext.accounts.doctype.payment_entry.test_payment_entry import create_company

		create_company()

	def tearDown(self):
		dummy = True  # pragma: no cover
		frappe.db.rollback()

	def _create_project(self):
		"""Create a unique project for each test"""
		project_name = f"test_project_{frappe.generate_hash(length=12)}"
		if not frappe.db.exists("Project", {"project_name": project_name}):
			frappe.get_doc(
				{"doctype": "Project", "company": "_Test Company", "project_name": project_name, "is_wbs": 1}
			).insert()
		return frappe.db.get_value("Project", {"project_name": project_name})

	def _create_wbs(self, project):
		"""Create a unique WBS for a given project"""
		wbs_name = f"test_wbs_{frappe.generate_hash(length=12)}"
		frappe.db.delete("WBS Monthly Distribution", {"for_wbs": wbs_name})
		wbs = frappe.get_doc(
			{
				"doctype": "Work Breakdown Structure",
				"project": project or "PROJ-0002",
				"wbs_name": wbs_name,
				"company": "_Test Company",
				"gl_account": "Cash - _TC",
			}
		)
		wbs.insert()
		return wbs

	def test_check_duplicate_for_wbs(self):
		project = self._create_project()
		wbs = self._create_wbs(project)

		wbs_md1 = frappe.get_doc({"doctype": "WBS Monthly Distribution", "for_wbs": wbs.name})
		wbs_md1.insert()

		wbs_md2 = frappe.get_doc({"doctype": "WBS Monthly Distribution", "for_wbs": wbs.name})
		with self.assertRaises(frappe.exceptions.ValidationError) as context:
			wbs_md2.insert()

		self.assertIn("A record with the same WBS already exists", str(context.exception))

	def test_wbs_monthly_distribution_update_linked_wbs(self):
		project = self._create_project()
		wbs = self._create_wbs(project)
		wbs.submit()
		self.assertEqual(wbs.docstatus, 1)

		wbs_md = frappe.get_doc({"doctype": "WBS Monthly Distribution", "for_wbs": wbs.name})
		wbs_md.insert()
		wbs.load_from_db()
		self.assertEqual(wbs.linked_monthly_distribution, wbs_md.name)

		wbs_md.delete()
		wbs.load_from_db()
		self.assertIsNone(wbs.linked_monthly_distribution)

	def test_check_total_allocation(self):
		project = self._create_project()

		def create_wbs_with_submit():
			wbs = self._create_wbs(project)
			wbs.submit()
			return wbs

		valid_wbs = create_wbs_with_submit()
		invalid_wbs = create_wbs_with_submit()

		# Helper to create distribution rows
		valid_months = [
			"January",
			"February",
			"March",
			"April",
			"May",
			"June",
			"July",
			"August",
			"September",
			"October",
			"November",
			"December",
		]

		def make_distribution_rows(values):
			return [{"month": valid_months[i % 12], "allocation": val} for i, val in enumerate(values)]

		# Valid allocation (sum <= 100)
		valid_md = frappe.get_doc(
			{
				"doctype": "WBS Monthly Distribution",
				"for_wbs": valid_wbs.name,
				"monthly_distribution": make_distribution_rows([60, 40]),
			}
		)
		valid_md.insert()
		self.assertTrue(valid_md.name)

		# Invalid allocation (sum > 100) should raise ValidationError
		invalid_md = frappe.get_doc(
			{
				"doctype": "WBS Monthly Distribution",
				"for_wbs": invalid_wbs.name,
				"monthly_distribution": make_distribution_rows([60, 50]),
			}
		)
		with self.assertRaises(frappe.exceptions.ValidationError) as context:
			invalid_md.insert()
		self.assertIn(
			"Total Monthly Distribution Allocation Percentage should not be more than 100%",
			str(context.exception),
		)