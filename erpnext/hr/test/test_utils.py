import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.data import today

from erpnext.hr.utils import validate_active_employee

test_dependencies = ["Employee"]


class TestUtils(FrappeTestCase):
	def test_validate_active_employee(self):
		active_employee = frappe.db.get_value("Employee", {"status": "Active", "relieving_date": None})
		validate_active_employee(active_employee, today())

		inactive_employee = frappe.db.get_value(
			"Employee", {"status": "Inactive", "relieving_date": ("<", today())}
		)
		self.assertRaises(frappe.ValidationError, validate_active_employee, inactive_employee, today())
