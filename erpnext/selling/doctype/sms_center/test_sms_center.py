# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee


class TestSMSCenter(IntegrationTestCase):
	def test_all_lead_open_query_selects_mobile_no(self):
		lead = frappe.get_doc(
			{"doctype": "Lead", "lead_name": "SMS Lead", "status": "Open", "mobile_no": "9800000001"}
		).insert()

		sms_center = frappe.new_doc("SMS Center")
		sms_center.send_to = "All Lead (Open)"
		rows = sms_center.get_contact_query_for_all_open_leads().run(as_list=1)

		self.assertIn([lead.lead_name, "9800000001"], rows)

	def test_receiver_nos_split_on_last_separator(self):
		sms_center = frappe.new_doc("SMS Center")
		sms_center.receiver_list = "Anne-Marie Roy - 9800000004\n+91-98000-00005\n9800000006"

		self.assertEqual(sms_center.get_receiver_nos(), ["9800000004", "+91-98000-00005", "9800000006"])

	def test_all_contact_includes_unlinked_and_dedupes_multi_link(self):
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "SMS Customer",
				"customer_type": "Company",
				"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}),
				"territory": frappe.db.get_value("Territory", {"is_group": 0}),
			}
		).insert()
		supplier = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": "SMS Supplier",
				"supplier_type": "Company",
				"supplier_group": frappe.db.get_value("Supplier Group", {"is_group": 0}),
			}
		).insert()

		unlinked = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "SMS Unlinked",
				"phone_nos": [{"phone": "9800000010", "is_primary_mobile_no": 1}],
			}
		).insert()

		multi = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "SMS Multi",
				"phone_nos": [{"phone": "9800000011", "is_primary_mobile_no": 1}],
				"links": [
					{"link_doctype": "Customer", "link_name": customer.name},
					{"link_doctype": "Supplier", "link_name": supplier.name},
				],
			}
		).insert()

		sms_center = frappe.new_doc("SMS Center")
		sms_center.send_to = "All Contact"
		numbers = [row[1] for row in sms_center.get_contact_query_for_all_contacts().run(as_list=1)]

		self.assertIn(unlinked.mobile_no, numbers)
		self.assertEqual(numbers.count(multi.mobile_no), 1)

	def test_all_sales_person_excludes_disabled_and_left(self):
		active_emp = make_employee(
			"sms-active@example.com", company="_Test Company", cell_number="9800000020"
		)
		left_emp = make_employee(
			"sms-left@example.com",
			company="_Test Company",
			cell_number="9800000021",
			status="Left",
			relieving_date="2020-01-01",
		)

		frappe.get_doc(
			{
				"doctype": "Sales Person",
				"sales_person_name": "SMS Active SP",
				"enabled": 1,
				"employee": active_emp,
			}
		).insert()
		frappe.get_doc(
			{
				"doctype": "Sales Person",
				"sales_person_name": "SMS Disabled SP",
				"enabled": 0,
				"employee": left_emp,
			}
		).insert()

		sms_center = frappe.new_doc("SMS Center")
		sms_center.send_to = "All Sales Person"
		numbers = [row[1] for row in sms_center.get_contact_query_for_all_sales_person().run(as_list=1)]

		self.assertIn("9800000020", numbers)
		self.assertNotIn("9800000021", numbers)
