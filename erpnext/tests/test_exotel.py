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
		data = {
			"CallSid": "23c162077629863c1a2d7f29263a162m",
			"CallFrom": "09999999991",
			"CallTo": "09999999980",
			"Direction": "incoming",
			"Created": "Wed, 23 Feb 2022 12:31:59",
			"From": "09999999991",
			"To": "09999999988",
			"CurrentTime": "2022-02-23 12:32:02",
			"DialWhomNumber": "09999999999",
			"Status": "busy",
			"EventType": "Dial",
			"AgentEmail": "test_employee_exotel@company.com",
		}
		end_call_data = {
			"CallSid": "23c162077629863c1a2d7f29263a162m",
			"CallFrom": "09999999991",
			"CallTo": "09999999980",
			"Direction": "incoming",
			"ForwardedFrom": "null",
			"Created": "Wed, 23 Feb 2022 12:31:59",
			"DialCallDuration": "17",
			"RecordingUrl": "https://s3-ap-southeast-1.amazonaws.com/exotelrecordings/erpnext/23c162077629863c1a2d7f29263a162n.mp3",
			"StartTime": "2022-02-23 12:31:58",
			"EndTime": "1970-01-01 05:30:00",
			"DialCallStatus": "completed",
			"CallType": "completed",
			"DialWhomNumber": "09999999999",
			"ProcessStatus": "null",
			"flow_id": "228040",
			"tenant_id": "67291",
			"From": "09999999991",
			"To": "09999999988",
			"RecordingAvailableBy": "Wed, 23 Feb 2022 12:37:25",
			"CurrentTime": "2022-02-23 12:32:25",
			"OutgoingPhoneNumber": "09999999988",
			"Legs": [
				{
					"Number": "09999999999",
					"Type": "single",
					"OnCallDuration": "10",
					"CallerId": "09999999980",
					"CauseCode": "NORMAL_CLEARING",
					"Cause": "16",
				}
			],
		}
		api_method = "handle_incoming_call"
		end_call_api_method = "handle_end_call"
		emulate_api_call(data, api_method, end_call_data, end_call_api_method)

		frappe.reload_doctype("Call Log")
		call_log = frappe.get_doc(
			"Call Log", {"from": "09999999991", "to": "09999999999", "status": "Completed"}
		)

		self.assertEqual(call_log.get("from"), "09999999991")
		self.assertEqual(call_log.get("to"), "09999999999")
		self.assertEqual(call_log.get("call_received_by"), "EMP-00001")
		self.assertEqual(call_log.get("status"), "Completed")

	def test_for_disconnected_call(self):
		data = {
			"CallSid": "d96421addce69e24bdc7ce5880d1162l",
			"CallFrom": "09999999991",
			"CallTo": "09999999980",
			"Direction": "incoming",
			"ForwardedFrom": "null",
			"Created": "Mon, 21 Feb 2022 15:58:12",
			"DialCallDuration": "0",
			"StartTime": "2022-02-21 15:58:12",
			"EndTime": "1970-01-01 05:30:00",
			"DialCallStatus": "canceled",
			"CallType": "client-hangup",
			"DialWhomNumber": "09999999999",
			"ProcessStatus": "null",
			"flow_id": "228040",
			"tenant_id": "67291",
			"From": "09999999991",
			"To": "09999999988",
			"CurrentTime": "2022-02-21 15:58:47",
			"OutgoingPhoneNumber": "09999999988",
			"Legs": [
				{
					"Number": "09999999999",
					"Type": "single",
					"OnCallDuration": "0",
					"CallerId": "09999999980",
					"CauseCode": "RING_TIMEOUT",
					"Cause": "1003",
				}
			],
		}
		api_method = "handle_missed_call"
		emulate_api_call(data, api_method)

		frappe.reload_doctype("Call Log")
		call_log = frappe.get_doc(
			"Call Log", {"from": "09999999991", "to": "09999999999", "status": "Canceled"}
		)

		self.assertEqual(call_log.get("from"), "09999999991")
		self.assertEqual(call_log.get("to"), "09999999999")
		self.assertEqual(call_log.get("call_received_by"), "EMP-00001")
		self.assertEqual(call_log.get("status"), "Canceled")

	def test_for_call_not_answered(self):
		data = {
			"CallSid": "fdb67a2b4b2d057b610a52ef43f81622",
			"CallFrom": "09999999991",
			"CallTo": "09999999980",
			"Direction": "incoming",
			"ForwardedFrom": "null",
			"Created": "Mon, 21 Feb 2022 15:47:02",
			"DialCallDuration": "0",
			"StartTime": "2022-02-21 15:47:02",
			"EndTime": "1970-01-01 05:30:00",
			"DialCallStatus": "no-answer",
			"CallType": "incomplete",
			"DialWhomNumber": "09999999999",
			"ProcessStatus": "null",
			"flow_id": "228040",
			"tenant_id": "67291",
			"From": "09999999991",
			"To": "09999999988",
			"CurrentTime": "2022-02-21 15:47:40",
			"OutgoingPhoneNumber": "09999999988",
			"Legs": [
				{
					"Number": "09999999999",
					"Type": "single",
					"OnCallDuration": "0",
					"CallerId": "09999999980",
					"CauseCode": "RING_TIMEOUT",
					"Cause": "1003",
				}
			],
		}
		api_method = "handle_missed_call"
		emulate_api_call(data, api_method)

		frappe.reload_doctype("Call Log")
		call_log = frappe.get_doc(
			"Call Log", {"from": "09999999991", "to": "09999999999", "status": "No Answer"}
		)

		self.assertEqual(call_log.get("from"), "09999999991")
		self.assertEqual(call_log.get("to"), "09999999999")
		self.assertEqual(call_log.get("call_received_by"), "EMP-00001")
		self.assertEqual(call_log.get("status"), "No Answer")

	def tearDown(self):
		frappe.db.rollback()


def emulate_api_call(data, api_method, end_call_data=None, end_call_api_method=None):
	# Build URL
	port = frappe.get_site_config().webserver_port or "8000"

	if os.environ.get("CI"):
		host = "localhost"
	else:
		host = frappe.local.site

	url = "http://{site}:{port}/api/method/erpnext.erpnext_integrations.exotel_integration.{api_method}".format(
		site=host, port=port, api_method=api_method
	)

	if end_call_data:
		end_call_url = "http://{site}:{port}/api/method/erpnext.erpnext_integrations.exotel_integration.{end_call_api_method}".format(
			site=host, port=port, end_call_api_method=end_call_api_method
		)

	requests.post(url=url, data=data)
	time.sleep(3)

	if end_call_data:
		requests.post(url=end_call_url, data=end_call_data)
		time.sleep(3)

	return
