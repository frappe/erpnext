# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import types
from unittest.mock import patch

import frappe

from erpnext.regional.italy.utils import (
	append_row_as_charges,
	get_conditions,
	get_e_invoice_attachments,
	get_unamended_name,
	set_payment_schedule_swift_number,
	update_summary_details,
)
from erpnext.tests.utils import ERPNextTestSuite


class TestItalyUtils(ERPNextTestSuite):
	"""Pure helpers behind the Italian e-invoice export."""

	def test_get_conditions_builds_filter_map(self):
		base = get_conditions({})
		self.assertEqual(base["docstatus"], 1)
		self.assertEqual(base["company_tax_id"], ("!=", ""))
		self.assertNotIn("company", base)

		scoped = get_conditions({"company": "_Test Company", "customer": "_Test Customer"})
		self.assertEqual(scoped["company"], "_Test Company")
		self.assertEqual(scoped["customer"], "_Test Customer")

		# a single bound uses >=/<=, both bounds use a between range
		self.assertEqual(get_conditions({"from_date": "2026-01-01"})["posting_date"], (">=", "2026-01-01"))
		self.assertEqual(get_conditions({"to_date": "2026-06-30"})["posting_date"], ("<=", "2026-06-30"))
		self.assertEqual(
			get_conditions({"from_date": "2026-01-01", "to_date": "2026-06-30"})["posting_date"],
			("between", ["2026-01-01", "2026-06-30"]),
		)

	def test_update_summary_details_accumulates_and_flags_exemption(self):
		summary = {}
		tax = frappe._dict(tax_exemption_reason="N4", tax_exemption_law="Art. 10")

		update_summary_details(summary, tax, 22.0, 44.0, 200.0)
		update_summary_details(summary, tax, 22.0, 22.0, 100.0)
		self.assertEqual(summary["22.0"]["tax_amount"], 66.0)
		self.assertEqual(summary["22.0"]["taxable_amount"], 300.0)
		# exemption fields are only populated for the zero-rate bucket
		self.assertEqual(summary["22.0"]["tax_exemption_reason"], "")

		update_summary_details(summary, tax, 0.0, 0.0, 500.0)
		self.assertEqual(summary["0.0"]["tax_exemption_reason"], "N4")
		self.assertEqual(summary["0.0"]["tax_exemption_law"], "Art. 10")

	def test_append_row_as_charges_computes_amount(self):
		items, summary = [], {}
		tax = frappe._dict(rate=22.0, account_head="VAT - IT", tax_exemption_reason="", tax_exemption_law="")
		reference_row = frappe._dict(tax_amount=200.0, description="Consulting")

		append_row_as_charges(items, tax, reference_row, summary)

		self.assertEqual(len(items), 1)
		row = items[0]
		self.assertEqual(row.tax_rate, 22.0)
		self.assertEqual(row.tax_amount, 44.0)  # 200 * 22 / 100
		self.assertEqual(row.taxable_amount, 200.0)
		self.assertEqual(row.item_code, "Consulting")
		self.assertEqual(row.item_tax_rate, {"VAT - IT": 22.0})
		self.assertEqual(summary["22.0"]["tax_amount"], 44.0)

	def test_get_unamended_name(self):
		# a doc missing the naming attributes is returned unchanged
		plain = types.SimpleNamespace(name="ACC-SINV-2026-00001")
		self.assertEqual(get_unamended_name(plain), "ACC-SINV-2026-00001")

		# an amended doc drops the trailing amendment suffix
		amended = frappe._dict(
			name="ACC-SINV-2026-00001-1",
			naming_series="ACC-SINV-.YYYY.-",
			amended_from="ACC-SINV-2026-00001",
		)
		self.assertEqual(get_unamended_name(amended), "ACC-SINV-2026-00001")

		# an original (non-amended) doc keeps its name
		original = frappe._dict(
			name="ACC-SINV-2026-00001", naming_series="ACC-SINV-.YYYY.-", amended_from=None
		)
		self.assertEqual(get_unamended_name(original), "ACC-SINV-2026-00001")

	def test_set_payment_schedule_swift_number_reads_bank(self):
		# the SWIFT code lives on Bank, not on Bank Account: it is read through the account's bank
		values = {
			("Bank Account", "_Test Bank Account", "bank"): "_Test Bank",
			("Bank", "_Test Bank", "swift_number"): "BCITITMM",
		}
		doc = frappe._dict(
			payment_schedule=[
				frappe._dict(bank_account="_Test Bank Account"),
				frappe._dict(bank_account=None, bank_account_swift_number="STALE"),
			]
		)

		with patch("frappe.get_cached_value", side_effect=lambda *args: values.get(args)):
			set_payment_schedule_swift_number(doc)

		self.assertEqual(doc.payment_schedule[0].bank_account_swift_number, "BCITITMM")
		self.assertIsNone(doc.payment_schedule[1].bank_account_swift_number)

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
