# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import now_datetime
from freezegun import freeze_time

from erpnext.startup.boot import boot_session
from erpnext.tests.utils import ERPNextTestSuite


class TestFiscalYear(ERPNextTestSuite):
	@freeze_time("1901-07-01")
	def test_replacing_fiscal_year_invalidates_cached_bootinfo(self):
		fiscal_year = frappe.get_doc(
			{
				"doctype": "Fiscal Year",
				"year": "_Test Fiscal Year Original 1901",
				"year_start_date": "1901-01-01",
				"year_end_date": "1901-12-31",
			}
		).insert()
		bootinfo = frappe._dict(sysdefaults=frappe._dict(), page_info=frappe._dict(), docs=[])
		boot_session(bootinfo)
		self.assertEqual(bootinfo.current_fiscal_year[0], fiscal_year.name)
		frappe.cache.hset("bootinfo", "test@example.com", bootinfo)
		self.addCleanup(frappe.cache.delete_value, "bootinfo")

		frappe.delete_doc("Fiscal Year", fiscal_year.name)
		self.assertIsNone(frappe.cache.hget("bootinfo", "test@example.com"))

		fiscal_year.year = "_Test Fiscal Year Replacement 1901"
		fiscal_year.name = None
		fiscal_year.insert()
		boot_session(bootinfo)
		self.assertEqual(bootinfo.current_fiscal_year[0], fiscal_year.name)

	def test_fiscal_year_insert_and_update_invalidate_cached_bootinfo(self):
		fiscal_year = frappe.get_doc(
			{
				"doctype": "Fiscal Year",
				"year": "_Test Fiscal Year Cache 1902",
				"year_start_date": "1902-01-01",
				"year_end_date": "1902-12-31",
			}
		)
		self.addCleanup(frappe.cache.delete_value, "bootinfo")
		for operation in (fiscal_year.insert, fiscal_year.save):
			with self.subTest(operation=operation.__name__):
				frappe.cache.hset("bootinfo", "test@example.com", {"current_fiscal_year": None})
				operation()
				self.assertIsNone(frappe.cache.hget("bootinfo", "test@example.com"))

				# Another request can populate bootinfo before this transaction commits.
				frappe.cache.hset("bootinfo", "test@example.com", {"current_fiscal_year": None})
				frappe.db.after_commit.run()
				self.assertIsNone(frappe.cache.hget("bootinfo", "test@example.com"))

	def test_extra_year(self):
		if frappe.db.exists("Fiscal Year", "_Test Fiscal Year 2000"):
			frappe.delete_doc("Fiscal Year", "_Test Fiscal Year 2000")

		fy = frappe.get_doc(
			{
				"doctype": "Fiscal Year",
				"year": "_Test Fiscal Year 2000",
				"year_end_date": "2002-12-31",
				"year_start_date": "2000-04-01",
			}
		)

		self.assertRaises(frappe.exceptions.InvalidDates, fy.insert)

	def test_company_fiscal_year_overlap(self):
		for name in ["_Test Global FY 2001", "_Test Company FY 2001"]:
			if frappe.db.exists("Fiscal Year", name):
				frappe.delete_doc("Fiscal Year", name)

		global_fy = frappe.new_doc("Fiscal Year")
		global_fy.year = "_Test Global FY 2001"
		global_fy.year_start_date = "2001-04-01"
		global_fy.year_end_date = "2002-03-31"
		global_fy.insert()

		company_fy = frappe.new_doc("Fiscal Year")
		company_fy.year = "_Test Company FY 2001"
		company_fy.year_start_date = "2001-01-01"
		company_fy.year_end_date = "2001-12-31"
		company_fy.append("companies", {"company": "_Test Company"})

		company_fy.insert()
		self.assertTrue(frappe.db.exists("Fiscal Year", global_fy.name))
		self.assertTrue(frappe.db.exists("Fiscal Year", company_fy.name))


def test_record_generator():
	test_records = [
		{
			"doctype": "Fiscal Year",
			"year": "_Test Short Fiscal Year 2011",
			"is_short_year": 1,
			"year_start_date": "2011-04-01",
			"year_end_date": "2011-12-31",
		}
	]

	start = 2012
	this_year = now_datetime().year
	end = now_datetime().year + 25
	# The current year fails to load with the following error:
	# Year start date or end date is overlapping with 2024. To avoid please set company
	# This is a quick-fix: if current FY is needed, please refactor test data properly
	for year in range(start, this_year):
		test_records.append(
			{
				"doctype": "Fiscal Year",
				"year": f"_Test Fiscal Year {year}",
				"year_start_date": f"{year}-01-01",
				"year_end_date": f"{year}-12-31",
			}
		)
	for year in range(this_year + 1, end):
		test_records.append(
			{
				"doctype": "Fiscal Year",
				"year": f"_Test Fiscal Year {year}",
				"year_start_date": f"{year}-01-01",
				"year_end_date": f"{year}-12-31",
			}
		)

	return test_records


test_records = test_record_generator()
