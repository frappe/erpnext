import frappe

from erpnext.regional.report.electronic_invoice_register.electronic_invoice_register import execute
from erpnext.tests.utils import ERPNextTestSuite


class TestElectronicInvoiceRegister(ERPNextTestSuite):
	def test_company_is_required(self):
		filters = frappe._dict(from_date="2026-01-01", to_date="2026-12-31")
		self.assertRaises(frappe.ValidationError, execute, filters)

		execute(frappe._dict(filters, company="_Test Company"))
