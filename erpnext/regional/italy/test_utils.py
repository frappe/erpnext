# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe

from erpnext.regional.italy.utils import get_e_invoice_attachments
from erpnext.tests.utils import ERPNextTestSuite


class TestItalyUtils(ERPNextTestSuite):
	def test_get_e_invoice_attachments_finds_existing_xml(self):
		# the existing XML must be found, otherwise `replace=True` adds a second one
		invoice = frappe._dict(name="_Test Italy E-Invoice 0001", company_tax_id="01234567890")
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "IT01234567890_00001.xml",
				"attached_to_doctype": "Sales Invoice",
				"attached_to_name": invoice.name,
				"content": "<FatturaElettronica/>",
				"is_private": 1,
			}
		).insert(ignore_permissions=True)

		self.assertEqual([attachment.name for attachment in get_e_invoice_attachments(invoice)], [file.name])
