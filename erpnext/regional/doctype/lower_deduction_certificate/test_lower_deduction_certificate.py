# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
import frappe
from frappe.utils import today

from erpnext.accounts.utils import get_fiscal_year
from erpnext.tests.utils import ERPNextTestSuite


class TestLowerDeductionCertificate(ERPNextTestSuite):
	def make_ldc(self, valid_from, valid_upto, fiscal_year=None):
		doc = frappe.new_doc("Lower Deduction Certificate")
		doc.valid_from = valid_from
		doc.valid_upto = valid_upto
		doc.fiscal_year = fiscal_year
		return doc

	def test_rate_and_limit_must_be_in_range(self):
		for rate, limit in ((-5, 50000), (100, 50000), (150, 50000), (1, 0), (1, -50000)):
			doc = frappe.new_doc("Lower Deduction Certificate", rate=rate, certificate_limit=limit)
			self.assertRaises(frappe.ValidationError, doc.validate_rate_and_limit)

		frappe.new_doc(
			"Lower Deduction Certificate", rate=0, certificate_limit=50000
		).validate_rate_and_limit()

	def test_pan_follows_the_supplier(self):
		supplier = frappe.get_doc(
			{
				"doctype": "Supplier",
				"supplier_name": "_Test LDC PAN Supplier",
				"supplier_group": "_Test Supplier Group",
				"tax_id": "AAAPA1234A",
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

	def test_used_certificate_cannot_be_changed_or_deleted(self):
		certificate = make_certificate()
		frappe.get_doc(
			{
				"doctype": "Tax Withholding Entry",
				"parent": "_Test Purchase Invoice",
				"parenttype": "Purchase Invoice",
				"parentfield": "tax_withholding_entries",
				"lower_deduction_certificate": certificate.name,
				"docstatus": 1,
			}
		).db_insert()

		certificate.rate = 0
		self.assertRaises(frappe.ValidationError, certificate.save)
		certificate.reload()
		certificate.certificate_limit = 200000
		certificate.save()

		frappe.db.set_value("Supplier", certificate.supplier, "tax_id", "DDDPD1234D")
		certificate.save()
		self.assertEqual(certificate.pan_no, "CCCPC1234C")
		certificate.pan_no = "DDDPD1234D"
		self.assertRaises(frappe.ValidationError, certificate.save)

		self.assertRaises(frappe.ValidationError, frappe.delete_doc, certificate.doctype, certificate.name)


def make_certificate():
	category = frappe.get_doc(
		{
			"doctype": "Tax Withholding Category",
			"name": "_Test LDC Category",
			"category_name": "_Test LDC Category",
		}
	).insert(ignore_mandatory=True)
	supplier = frappe.get_doc(
		{"doctype": "Supplier", "supplier_name": "_Test LDC Used Supplier", "tax_id": "CCCPC1234C"}
	).insert()
	fy_name, fy_start, fy_end = get_fiscal_year(today(), company="_Test Company")
	return frappe.get_doc(
		{
			"doctype": "Lower Deduction Certificate",
			"certificate_no": "_TEST-LDC-USED",
			"company": "_Test Company",
			"supplier": supplier.name,
			"tax_withholding_category": category.name,
			"fiscal_year": fy_name,
			"valid_from": fy_start,
			"valid_upto": fy_end,
			"rate": 1,
			"certificate_limit": 100000,
		}
	).insert()
