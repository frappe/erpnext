import unittest
import frappe
from erpnext.crm.report.sales_pipeline_analytics.sales_pipeline_analytics import execute

class TestSalesPipelineAnalytics(unittest.TestCase):
    
    @classmethod
    def setUpClass(self):
        create_company()
        create_customer()
        create_lead()
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
            'company':"__Test Company"
        }

        report = execute(filters)

        expected_data = [
            {
                'opportunity_owner':'[]',
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
            'company':"__Test Company"
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
            'company':"__Test Company"
        }

        report = execute(filters)

        expected_data = [
            {
                'opportunity_owner':'[]',
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
            'company':"__Test Company"
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
            'range':"Quaterly",
            'based_on':"Number",
            'status':"Open",
            'opportunity_type':"Sales",
            'company':"__Test Company"
        }

        report = execute(filters)

        expected_data = [
            {
                'opportunity_owner':'[]',
                'Q3':1
            }
        ]

        self.assertEqual(expected_data,report[1])

        filters = {
            'pipeline_by':"Sales Stage",
            'range':"Quaterly",
            'based_on':"Number",
            'status':"Open",
            'opportunity_type':"Sales",
            'company':"__Test Company"
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
            'range':"Quaterly",
            'based_on':"Amount",
            'status':"Open",
            'opportunity_type':"Sales",
            'company':"__Test Company"
        }

        report = execute(filters)

        expected_data = [
            {
                'opportunity_owner':'[]',
                'Q3':150000
            }
        ]

        self.assertEqual(expected_data,report[1])

        filters = {
            'pipeline_by':"Sales Stage",
            'range':"Quaterly",
            'based_on':"Amount",
            'status':"Open",
            'opportunity_type':"Sales",
            'company':"__Test Company"
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
            'company':"__Test Company",
            'opportunity_source':'Cold Calling',
            'from_date': '2021-08-01',
            'to_date':'2021-08-31'
        }

        report = execute(filters)

        expected_data = [
            {
                'opportunity_owner':'[]',
                'August': 1
            }
        ]

        self.assertEqual(expected_data,report[1])


def create_company():
    doc = frappe.db.exists('Company','__Test Company')
    if not doc:
        doc = frappe.new_doc('Company')
        doc.company_name = '__Test Company'
        doc.abbr = "_TC"
        doc.default_currency = "INR"
        doc.insert()

def create_customer():
    doc = frappe.db.exists("Customer","_Test Customer")
    if not doc:
        doc = frappe.new_doc("Customer")
        doc.customer_name = '_Test Customer'
        doc.insert()

def create_lead():
    doc = frappe.db.exists("Lead","_Test Lead")
    if not doc:
        doc = frappe.new_doc("Lead")
        doc.lead_name = '_Test Lead'
        doc.company_name = 'Client Company'
        doc.company = "__Test Company"
        doc.insert()

def create_opportunity():
    doc = frappe.db.exists({
        "doctype":"Opportunity",
        "title":"Client Company"
        })
    if not doc:
        doc = frappe.new_doc("Opportunity")
        doc.opportunity_from = "Lead"
        lead_name = frappe.db.get_value("Lead",{"company":'__Test Company'},['name'])
        doc.party_name = lead_name
        doc.opportunity_amount = 150000
        doc.source = "Cold Calling"
        doc.expected_closing = "2021-08-31"
        doc.company = "__Test Company"
        doc.insert()