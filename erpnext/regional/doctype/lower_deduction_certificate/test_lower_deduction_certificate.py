# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from erpnext.accounts.doctype.tax_withholding_category.test_tax_withholding_category import (
	make_pan_no_field,
)
from erpnext.accounts.utils import get_fiscal_year

test_dependencies = ["Supplier Group"]


class TestLowerDeductionCertificate(FrappeTestCase):
	def make_ldc(self, valid_from, valid_upto, fiscal_year=None):
		doc = frappe.new_doc("Lower Deduction Certificate")
		doc.valid_from = valid_from
		doc.valid_upto = valid_upto
		doc.fiscal_year = fiscal_year
		return doc

	def test_pan_follows_the_supplier(self):
		make_pan_no_field()
		supplier = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": "_Test LDC PAN Supplier",
				"supplier_group": "_Test Supplier Group",
				"pan": "AAAPA1234A",
			}
		).insert()

		fy_name, fy_start, fy_end = get_fiscal_year(today())
		doc = self.make_ldc(fy_start, fy_end, fiscal_year=fy_name)
		doc.update(
			{
				"company": "_Test Company",
				"supplier": supplier.name,
				"pan_no": "BBBPB1234B",
				"certificate_limit": 1,
			}
		)
		doc.validate()
		self.assertEqual(doc.pan_no, "AAAPA1234A")
