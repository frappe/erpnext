from unittest.mock import patch

import frappe
from frappe.utils import add_days, getdate, nowdate

from erpnext.maintenance.doctype.maintenance_schedule.maintenance_schedule import (
	get_serial_no_query,
	get_serial_nos_from_schedule,
	make_maintenance_visit,
)
from erpnext.stock.doctype.delivery_note.mapper import make_installation_note
from erpnext.stock.doctype.item.test_item import make_item
from erpnext.tests.utils import ERPNextTestSuite


class TestSerialBatchServices(ERPNextTestSuite):
	def setUp(self):
		self.item = make_item("_Identity Service Item A", {"has_serial_no": 1})
		self.other_item = make_item("_Identity Service Item B", {"has_serial_no": 1})
		self.serial = self.make_serial(self.item.name, "Service-001")
		self.other_serial = self.make_serial(self.other_item.name, "Service-001")

	def test_installation_uses_physical_text_and_checks_delivery_serials(self):
		delivery = frappe.get_doc(
			doctype="Delivery Note", docstatus=1, company="_Test Company", customer="_Test Customer"
		)
		delivery.db_insert()
		bundle = self.make_bundle(self.serial.name, "Delivery Note")
		row = delivery.append(
			"items",
			{
				"item_code": self.item.name,
				"qty": 1,
				"installed_qty": 0,
				"serial_and_batch_bundle": bundle.name,
			},
		)
		row.db_insert()
		note = make_installation_note(delivery.name)
		self.assertEqual(note.items[0].serial_no, "Service-001")
		self.assertFalse(note.items[0].serial_and_batch_bundle)
		note.items[0].serial_no = "service-001"
		note.validate_serial_no()
		self.assertEqual(note.items[0].serial_no, "service-001")
		note.items[0].item_code = self.other_item.name
		with self.assertRaisesRegex(frappe.ValidationError, "Service-001.*Delivery Note"):
			note.validate_serial_no()

	def test_installation_rejects_duplicate_case_variants(self):
		note = frappe.get_doc(
			doctype="Installation Note",
			items=[{"item_code": self.item.name, "qty": 2, "serial_no": "Service-001\nservice-001"}],
		)
		with self.assertRaisesRegex(frappe.ValidationError, "entered more than once"):
			note.validate_serial_no()

	def test_schedule_generates_physical_text_from_bundles(self):
		bundle = self.make_bundle(self.serial.name, "Maintenance Schedule")
		schedule = self.make_schedule(serial_and_batch_bundle=bundle.name)
		with patch.object(schedule, "create_schedule_list", return_value=[getdate(nowdate())]):
			schedule.generate_schedule()
		self.assertEqual(schedule.schedules[0].serial_no, "Service-001")
		self.assertEqual(schedule.items[0].serial_and_batch_bundle, bundle.name)
		schedule.items[0].item_code = self.other_item.name
		with self.assertRaisesRegex(frappe.ValidationError, "does not belong to Item"):
			schedule.generate_schedule()

	def test_schedule_serial_text_updates_amc_on_submit_and_cancel(self):
		schedule = self.make_schedule(serial_no="Service-001")
		schedule.append("schedules", {"item_code": self.item.name, "serial_no": "Service-001"})
		schedule.db_insert()
		schedule.on_submit()
		self.assertEqual(getdate(self.serial.reload().amc_expiry_date), getdate(schedule.items[0].end_date))
		self.assertFalse(self.other_serial.reload().amc_expiry_date)
		schedule.on_cancel()
		self.assertFalse(self.serial.reload().amc_expiry_date)

	def test_schedule_query_and_visit_mapping_return_item_specific_ids(self):
		schedule = self.make_schedule(serial_no="Service-001")
		schedule.docstatus = 1
		schedule.db_insert()
		schedule.items[0].db_insert()
		detail = schedule.append(
			"schedules",
			{
				"item_code": self.item.name,
				"serial_no": "Service-001",
				"item_reference": schedule.items[0].name,
			},
		)
		detail.db_insert()
		self.assertEqual(get_serial_nos_from_schedule(self.item.name, schedule.name), [self.serial.name])
		rows = get_serial_no_query(
			"Serial No",
			"service-001",
			"name",
			0,
			20,
			{"item_code": self.item.name, "schedule": schedule.name},
		)
		self.assertEqual([tuple(row) for row in rows], [(self.serial.name, "Service-001")])
		visit = make_maintenance_visit(schedule.name)
		self.assertEqual(visit.purposes[0].serial_no, self.serial.name)
		with self.set_user("Guest"), self.assertRaises(frappe.PermissionError):
			get_serial_nos_from_schedule(self.item.name, schedule.name)

	def test_service_links_reject_a_serial_from_another_item(self):
		visit = frappe.get_doc(
			doctype="Maintenance Visit",
			purposes=[{"item_code": self.item.name, "serial_no": self.other_serial.name}],
		)
		claim = frappe.get_doc(
			doctype="Warranty Claim", item_code=self.item.name, serial_no=self.other_serial.name
		)
		for doc in (visit, claim):
			with self.subTest(doctype=doc.doctype), self.assertRaisesRegex(
				frappe.ValidationError, "Service-001.*does not belong to Item"
			):
				doc.validate_serial_no()

	def make_serial(self, item_code, number):
		return frappe.get_doc(
			doctype="Serial No", item_code=item_code, serial_no=number, company="_Test Company"
		).insert()

	def make_schedule(self, **values):
		return frappe.get_doc(
			doctype="Maintenance Schedule",
			company="_Test Company",
			customer="_Test Customer",
			items=[
				{
					"item_code": self.item.name,
					"start_date": nowdate(),
					"end_date": add_days(nowdate(), 30),
					"no_of_visits": 1,
					**values,
				}
			],
		)

	def make_bundle(self, serial_id, voucher_type):
		bundle = frappe.get_doc(
			doctype="Serial and Batch Bundle", item_code=self.item.name, voucher_type=voucher_type
		)
		bundle.db_insert()
		bundle.append("entries", {"serial_no": serial_id, "qty": 1}).db_insert()
		return bundle
