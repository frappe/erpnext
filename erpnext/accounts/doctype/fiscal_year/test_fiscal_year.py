# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import unittest

import frappe
from frappe.utils import now_datetime
from datetime import date

test_ignore = ["Company"]


class TestFiscalYear(unittest.TestCase):
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

	def test_cannot_change_fiscal_year_dates_TC_ACC_337(self):
		fy_name = "_Test Fiscal Year Change"

		if frappe.db.exists("Fiscal Year", fy_name):
			frappe.delete_doc("Fiscal Year", fy_name, force=True)

		fy = frappe.get_doc({
			"doctype": "Fiscal Year",
			"year": fy_name,
			"year_start_date": "2090-04-01",
			"year_end_date": "2091-03-31",
		})
		fy.insert(ignore_permissions=True)

		fy = frappe.get_doc("Fiscal Year", fy.name)
		fy.year_start_date = "2090-01-01"
		fy.year_end_date = "2090-12-31"

		with self.assertRaises(frappe.exceptions.ValidationError) as e:
			fy.save()

		self.assertIn(
			"Cannot change Fiscal Year Start Date and Fiscal Year End Date once the Fiscal Year is saved.",
			str(e.exception),
		)
  
	def test_auto_create_fiscal_year_TC_ACC_338(self):
		from frappe.utils import add_days, getdate, add_years
		from erpnext.accounts.doctype.fiscal_year.fiscal_year import auto_create_fiscal_year
		import random, string
		from datetime import timedelta
  
		suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
		company_name = f"_Test Company FY {suffix}"
		abbr = f"_TCF{suffix}"

		company_doc = frappe.get_doc({
			"doctype": "Company",
			"company_name": company_name,
			"abbr": abbr,
			"default_currency": "INR"
		}).insert(ignore_permissions=True)

		fy_name = f"_Test FY AutoCreate {suffix}"

		end_date = add_days(getdate(), 3)
		start_date = add_years(end_date, -1) + timedelta(days=1)

		for fy in frappe.get_all(
			"Fiscal Year",
			filters=[
				["year_start_date", "<=", end_date],
				["year_end_date", ">=", start_date],
			],
			fields=["name"]
		):
			frappe.delete_doc("Fiscal Year", fy.name, force=True)

		fy = frappe.get_doc({
			"doctype": "Fiscal Year",
			"year": fy_name,
			"year_start_date": start_date,
			"year_end_date": end_date,
			"companies": [{"company": company_name}]
		})
		fy.insert(ignore_permissions=True)

		auto_create_fiscal_year()

		new_fy_start = add_days(end_date, 1)
		new_fy_end = add_years(end_date, 1)

		new_fy = frappe.db.exists(
			"Fiscal Year",
			{"year_start_date": new_fy_start, "year_end_date": new_fy_end}
		)

		frappe.delete_doc("Fiscal Year", fy.name, force=True)
		if new_fy:
			frappe.delete_doc("Fiscal Year", new_fy, force=True)
		frappe.delete_doc("Company", company_name, force=True)
 
 
	def test_get_from_and_to_date_TC_ACC_381(self):
		from erpnext.accounts.doctype.fiscal_year.fiscal_year import get_from_and_to_date
		from frappe.utils import getdate, add_years
		from datetime import timedelta

		fy_name = "_Test FY GetFromTo"
		start_date = getdate()
		end_date = add_years(start_date, 1) - timedelta(days=1)

		for fy in frappe.get_all(
			"Fiscal Year",
			filters=[
				["year_start_date", "<=", end_date],
				["year_end_date", ">=", start_date],
			],
			fields=["name"]
		):
			frappe.delete_doc("Fiscal Year", fy.name, force=True)

		if frappe.db.exists("Fiscal Year", fy_name):
			frappe.delete_doc("Fiscal Year", fy_name, force=True)

		fy = frappe.get_doc({
			"doctype": "Fiscal Year",
			"year": fy_name,
			"year_start_date": start_date,
			"year_end_date": end_date,
			"companies": [{"company": "_Test Company"}]
		})
		fy.insert(ignore_permissions=True)

		result = get_from_and_to_date(fy_name)

		self.assertEqual(result["from_date"], start_date)
		self.assertEqual(result["to_date"], end_date)

		frappe.delete_doc("Fiscal Year", fy_name, force=True)

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
	end = now_datetime().year + 25
	for year in range(start, end):
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