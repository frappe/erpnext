import unittest

import frappe

from erpnext.crm.report.sales_pipeline_analytics.sales_pipeline_analytics import execute


class TestSalesPipelineAnalytics(unittest.TestCase):
	@classmethod
	def setUpClass(self):
		frappe.db.delete("Opportunity")
		create_company()
		create_customer()
		create_opportunity()

	def test_sales_pipeline_analytics(self):
		self.check_for_monthly_and_number()
		self.check_for_monthly_and_amount()
		self.check_for_quarterly_and_number()
		self.check_for_quarterly_and_amount()
		self.check_for_all_filters()

	def check_for_monthly_and_number(self):
		filters = {
			'pipeline_by':"Owner",
			'range':"Monthly",
			'based_on':"Number",
			'status':"Open",
			'opportunity_type':"Sales",
			'company':"Best Test"
		}

		report = execute(filters)

		expected_data = [
			{
				'opportunity_owner':'Not Assigned',
				'August':1
			}
		]

		self.assertEqual(expected_data,report[1])

		filters = {
			'pipeline_by':"Sales Stage",
			'range':"Monthly",
			'based_on':"Number",
			'status':"Open",
			'opportunity_type':"Sales",
			'company':"Best Test"
		}

		report = execute(filters)

		expected_data = [
			{
				'sales_stage':'Prospecting',
				'August':1
			}
		]

		self.assertEqual(expected_data,report[1])

	def check_for_monthly_and_amount(self):
		filters = {
			'pipeline_by':"Owner",
			'range':"Monthly",
			'based_on':"Amount",
			'status':"Open",
			'opportunity_type':"Sales",
			'company':"Best Test"
		}

		report = execute(filters)

		expected_data = [
			{
				'opportunity_owner':'Not Assigned',
				'August':150000
			}
		]

		self.assertEqual(expected_data,report[1])

		filters = {
			'pipeline_by':"Sales Stage",
			'range':"Monthly",
			'based_on':"Amount",
			'status':"Open",
			'opportunity_type':"Sales",
			'company':"Best Test"
		}

		report = execute(filters)

		expected_data = [
			{
				'sales_stage':'Prospecting',
				'August':150000
			}
		]

		self.assertEqual(expected_data,report[1])

	def check_for_quarterly_and_number(self):
		filters = {
			'pipeline_by':"Owner",
			'range':"Quarterly",
			'based_on':"Number",
			'status':"Open",
			'opportunity_type':"Sales",
			'company':"Best Test"
		}

		report = execute(filters)

		expected_data = [
			{
				'opportunity_owner':'Not Assigned',
				'Q3':1
			}
		]

		self.assertEqual(expected_data,report[1])

		filters = {
			'pipeline_by':"Sales Stage",
			'range':"Quarterly",
			'based_on':"Number",
			'status':"Open",
			'opportunity_type':"Sales",
			'company':"Best Test"
		}

		report = execute(filters)

		expected_data = [
			{
				'sales_stage':'Prospecting',
				'Q3':1
			}
		]

		self.assertEqual(expected_data,report[1])

	def check_for_quarterly_and_amount(self):
		filters = {
			'pipeline_by':"Owner",
			'range':"Quarterly",
			'based_on':"Amount",
			'status':"Open",
			'opportunity_type':"Sales",
			'company':"Best Test"
		}

		report = execute(filters)

		expected_data = [
			{
				'opportunity_owner':'Not Assigned',
				'Q3':150000
			}
		]

		self.assertEqual(expected_data,report[1])

		filters = {
			'pipeline_by':"Sales Stage",
			'range':"Quarterly",
			'based_on':"Amount",
			'status':"Open",
			'opportunity_type':"Sales",
			'company':"Best Test"
		}

		report = execute(filters)

		expected_data = [
			{
				'sales_stage':'Prospecting',
				'Q3':150000
			}
		]

		self.assertEqual(expected_data,report[1])

	def check_for_all_filters(self):
		filters = {
			'pipeline_by':"Owner",
			'range':"Monthly",
			'based_on':"Number",
			'status':"Open",
			'opportunity_type':"Sales",
			'company':"Best Test",
			'opportunity_source':'Cold Calling',
			'from_date': '2021-08-01',
			'to_date':'2021-08-31'
		}

		report = execute(filters)

		expected_data = [
			{
				'opportunity_owner':'Not Assigned',
				'August': 1
			}
		]

		self.assertEqual(expected_data,report[1])

def create_company():
	doc = frappe.db.exists('Company','Best Test')
	if not doc:
		doc = frappe.new_doc('Company')
		doc.company_name = 'Best Test'
		doc.default_currency = "INR"
		doc.insert()

def create_customer():
	doc = frappe.db.exists("Customer","_Test NC")
	if not doc:
		doc = frappe.new_doc("Customer")
		doc.customer_name = '_Test NC'
		doc.insert()

def create_opportunity():
	doc = frappe.db.exists({"doctype":"Opportunity","party_name":"_Test NC"})
	if not doc:
		doc = frappe.new_doc("Opportunity")
		doc.opportunity_from = "Customer"
		customer_name = frappe.db.get_value("Customer",{"customer_name":'_Test NC'},['customer_name'])
		doc.party_name = customer_name
		doc.opportunity_amount = 150000
		doc.source = "Cold Calling"
		doc.currency = "INR"
		doc.expected_closing = "2021-08-31"
		doc.company = 'Best Test'
		doc.insert()