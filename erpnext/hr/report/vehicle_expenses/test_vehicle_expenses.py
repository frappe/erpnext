# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import unittest

import frappe
from frappe.utils import getdate

from erpnext.accounts.utils import get_fiscal_year
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.vehicle_log.test_vehicle_log import get_vehicle, make_vehicle_log
from erpnext.hr.doctype.vehicle_log.vehicle_log import make_expense_claim
from erpnext.hr.report.vehicle_expenses.vehicle_expenses import execute


class TestVehicleExpenses(unittest.TestCase):
	@classmethod
	def setUpClass(self):
		frappe.db.sql('delete from `tabVehicle Log`')

		employee_id = frappe.db.sql('''select name from `tabEmployee` where name="testdriver@example.com"''')
		self.employee_id = employee_id[0][0] if employee_id else None
		if not self.employee_id:
			self.employee_id = make_employee('testdriver@example.com', company='_Test Company')

		self.license_plate = get_vehicle(self.employee_id)

	def test_vehicle_expenses_based_on_fiscal_year(self):
		vehicle_log = make_vehicle_log(self.license_plate, self.employee_id, with_services=True)
		expense_claim = make_expense_claim(vehicle_log.name)

		# Based on Fiscal Year
		filters = {
			'filter_based_on': 'Fiscal Year',
			'fiscal_year': get_fiscal_year(getdate())[0]
		}

		report = execute(filters)

		expected_data = [{
			'vehicle': self.license_plate,
			'make': 'Maruti',
			'model': 'PCM',
			'location': 'Mumbai',
			'log_name': vehicle_log.name,
			'odometer': 5010,
			'date': getdate(),
			'fuel_qty': 50.0,
			'fuel_price': 500.0,
			'fuel_expense': 25000.0,
			'service_expense': 2000.0,
			'employee': self.employee_id
		}]

		self.assertEqual(report[1], expected_data)

		# Based on Date Range
		fiscal_year = get_fiscal_year(getdate(), as_dict=True)
		filters = {
			'filter_based_on': 'Date Range',
			'from_date': fiscal_year.year_start_date,
			'to_date': fiscal_year.year_end_date
		}

		report = execute(filters)
		self.assertEqual(report[1], expected_data)

		# clean up
		vehicle_log.cancel()
		frappe.delete_doc('Expense Claim', expense_claim.name)
		frappe.delete_doc('Vehicle Log', vehicle_log.name)

	def tearDown(self):
		frappe.delete_doc('Vehicle', self.license_plate, force=1)
		frappe.delete_doc('Employee', self.employee_id, force=1)
