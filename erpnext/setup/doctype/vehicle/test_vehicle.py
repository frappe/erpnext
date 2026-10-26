# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.utils import add_days, random_string

from erpnext.setup.doctype.vehicle import vehicle_dashboard
from erpnext.tests.utils import ERPNextTestSuite


class TestVehicle(ERPNextTestSuite):
	def make_vehicle(self, **kwargs):
		vehicle_args = {
			"doctype": "Vehicle",
			"license_plate": random_string(10).upper(),
			"make": "Maruti",
			"model": "PCM",
			"last_odometer": 5000,
			"acquisition_date": frappe.utils.nowdate(),
			"location": "Mumbai",
			"chassis_no": "1234ABCD",
			"uom": "Litre",
			"vehicle_value": frappe.utils.flt(500000),
		}
		vehicle_args.update(kwargs)
		return frappe.get_doc(vehicle_args)

	def test_make_vehicle(self):
		self.make_vehicle().insert()

	def test_incomplete_insurance_dates_are_valid(self):
		for insurance_dates in (
			{"start_date": add_days(frappe.utils.nowdate(), 1)},
			{"end_date": add_days(frappe.utils.nowdate(), -1)},
		):
			self.make_vehicle(**insurance_dates).insert()

	def test_dashboard_excludes_vehicle_log_without_doctype(self):
		with patch("frappe.db.exists", autospec=True, return_value=False):
			dashboard = vehicle_dashboard.get_data()

		self.assertEqual(dashboard["transactions"], [{"items": ["Delivery Trip"]}])

	def test_dashboard_includes_vehicle_log_with_doctype(self):
		with patch("frappe.db.exists", autospec=True, return_value=True):
			dashboard = vehicle_dashboard.get_data()

		self.assertEqual(
			dashboard["transactions"], [{"items": ["Vehicle Log"]}, {"items": ["Delivery Trip"]}]
		)

	def test_renaming_vehicle(self):
		license_plate = random_string(10).upper()

		vehicle = frappe.get_doc(
			{
				"doctype": "Vehicle",
				"license_plate": license_plate,
				"make": "Skoda",
				"model": "Slavia",
				"last_odometer": 5000,
				"acquisition_date": frappe.utils.nowdate(),
				"location": "Mumbai",
				"chassis_no": "1234EFGH",
				"uom": "Litre",
				"vehicle_value": frappe.utils.flt(500000),
			}
		)
		vehicle.insert()

		new_license_plate = random_string(10).upper()
		frappe.rename_doc("Vehicle", license_plate, new_license_plate)

		self.assertEqual(
			new_license_plate, frappe.db.get_value("Vehicle", new_license_plate, "license_plate")
		)
