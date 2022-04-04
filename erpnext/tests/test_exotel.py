import os
import time
import unittest

import frappe
import requests
from frappe.contacts.doctype.contact.test_contact import create_contact

from erpnext.hr.doctype.employee.test_employee import make_employee


class TestExotel(unittest.TestCase):
	def setUp(self):
		make_employee("test_employee_exotel@company.com", cell_number="9999999999")
		phones = [{"phone": "+91 9999999991", "is_primary_phone": 0, "is_primary_mobile_no": 1}]
		create_contact("Test Contact", "Mr", phones=phones)

	def test_for_successful_call(self):
		from .exotel_test_data import call_end_data, call_initiation_data

		api_method = "handle_incoming_call"
		end_call_api_method = "handle_end_call"

		emulate_api_call(call_initiation_data, api_method)
		emulate_api_call(call_end_data, end_call_api_method)

		call_log = frappe.get_doc("Call Log", call_initiation_data.CallSid)

		self.assertEqual(call_log.get("from"), call_initiation_data.CallFrom)
		self.assertEqual(call_log.get("to"), call_initiation_data.DialWhomNumber)
		self.assertEqual(call_log.get("call_received_by"), "EMP-00001")
		self.assertEqual(call_log.get("status"), "Completed")

	def test_for_disconnected_call(self):
		from .exotel_test_data import call_disconnected_data

		api_method = "handle_missed_call"
		emulate_api_call(call_disconnected_data, api_method)
		call_log = frappe.get_doc("Call Log", call_disconnected_data.CallSid)

		self.assertEqual(call_log.get("from"), call_disconnected_data.CallFrom)
		self.assertEqual(call_log.get("to"), call_disconnected_data.DialWhomNumber)
		self.assertEqual(call_log.get("call_received_by"), "EMP-00001")
		self.assertEqual(call_log.get("status"), "Canceled")

	def test_for_call_not_answered(self):
		from .exotel_test_data import call_not_answered_data

		api_method = "handle_missed_call"
		emulate_api_call(call_not_answered_data, api_method)

		call_log = frappe.get_doc("Call Log", call_not_answered_data.CallSid)

		self.assertEqual(call_log.get("from"), call_not_answered_data.CallFrom)
		self.assertEqual(call_log.get("to"), call_not_answered_data.DialWhomNumber)
		self.assertEqual(call_log.get("call_received_by"), "EMP-00001")
		self.assertEqual(call_log.get("status"), "No Answer")

	def tearDown(self):
		frappe.db.rollback()


def emulate_api_call(data, api_method):
	# Build URL
	url = get_exotel_handler_endpoint(api_method)
	res = requests.post(url=url, data=frappe.as_json(data))
	res.raise_for_status()
	time.sleep(1)


def get_exotel_handler_endpoint(method):
	site = "localhost" if os.environ.get("CI") else frappe.local.site
	port = frappe.get_site_config().webserver_port or "8000"
	return f"http://{site}:{port}/api/method/erpnext.erpnext_integrations.exotel_integration.{method}"
