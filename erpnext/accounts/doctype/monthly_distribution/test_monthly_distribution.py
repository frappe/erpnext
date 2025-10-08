# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and Contributors
# See license.txt


import unittest
import frappe
from frappe.utils import add_months, flt
test_records = frappe.get_test_records("Monthly Distribution")
from frappe.utils import flt

class TestMonthlyDistribution(unittest.TestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_get_months_and_validate_in_monthly_distribution_TC_ACC_350(self):
		doc = frappe.new_doc("Monthly Distribution")
		doc.get_months()
  
		self.assertEqual(len(doc.percentages), 12)
		self.assertAlmostEqual(sum(flt(d.percentage_allocation) for d in doc.percentages), 100.0, places=2)
		doc.validate() 

		doc.percentages[0].percentage_allocation = 5.0 
		doc.percentages[1].percentage_allocation = 5.0 

		with self.assertRaises(frappe.ValidationError) as cm:
			doc.validate()
   
		self.assertIn("Percentage Allocation should be equal to 100%", str(cm.exception))
  
	def test_get_periodwise_distribution_data_TC_ACC_351(self):
		from erpnext.accounts.doctype.monthly_distribution.monthly_distribution import get_periodwise_distribution_data
		dist = frappe.new_doc("Monthly Distribution")
		dist.distribution_id = "Test Distribution 1"
		dist.get_months()
		dist.save()

		from datetime import datetime

		period_list = [
			frappe._dict(key="Q1", from_date=datetime(2025, 1, 1)),
			frappe._dict(key="Q2", from_date=datetime(2025, 4, 1)),
			frappe._dict(key="Q3", from_date=datetime(2025, 7, 1)),
			frappe._dict(key="Q4", from_date=datetime(2025, 10, 1)),
		]

		data = get_periodwise_distribution_data(dist.name, period_list, "Quarterly")

		self.assertEqual(set(data.keys()), {"Q1", "Q2", "Q3", "Q4"})

		for val in data.values():
			self.assertAlmostEqual(val, 25.0, places=2)
   
	def test_get_percentage_TC_ACC_352(self):
		from erpnext.accounts.doctype.monthly_distribution.monthly_distribution import get_percentage
		from datetime import datetime

		doc = frappe.new_doc("Monthly Distribution")
		doc.distribution_id = "Test Distribution 003"
		doc.get_months()
		doc.save()

		start_date = datetime(2025, 1, 1)

		result = get_percentage(doc, start_date, 3)
		self.assertAlmostEqual(result, 25.0, places=2)

		result = get_percentage(doc, start_date, 6)
		self.assertAlmostEqual(result, 50.0, places=2)

		result = get_percentage(doc, start_date, 1)
		self.assertAlmostEqual(result, 100.0 / 12, places=2)

		april_date = datetime(2025, 4, 1)
		result = get_percentage(doc, april_date, 3) 
		self.assertAlmostEqual(result, 25.0, places=2)

