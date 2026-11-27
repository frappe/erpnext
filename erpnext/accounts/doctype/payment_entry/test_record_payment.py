import frappe
from frappe.utils import add_days, nowdate

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.payment_entry.record_payment import get_unapplied_credit, record_payment
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.tests.utils import ERPNextTestSuite


class TestRecordPayment(ERPNextTestSuite):
	def setUp(self):
		frappe.db.set_value("Company", "_Test Company", "write_off_account", "Write Off - _TC")

	def test_full_payment_submits_and_settles_invoice(self):
		invoice = create_sales_invoice(rate=1000)
		payment = record(invoice, party_amount=1000)

		self.assertEqual(payment.docstatus, 1)
		self.assertEqual(payment.references[0].allocated_amount, 1000)
		self.assertEqual(get_outstanding(invoice), 0)

	def test_one_payment_settles_oldest_invoice_first(self):
		newer = create_sales_invoice(rate=1000)
		older = create_sales_invoice(rate=1000, posting_date=add_days(nowdate(), -10))

		payment = record(newer, older, party_amount=1500)

		self.assertEqual([row.reference_name for row in payment.references], [older.name, newer.name])
		self.assertEqual(get_outstanding(older), 0)
		self.assertEqual(get_outstanding(newer), 500)

	def test_write_off_settles_short_payment(self):
		for invoice, sign in (
			(create_sales_invoice(rate=1000), 1),
			(make_purchase_invoice(qty=1, rate=1000), -1),
		):
			payment = record(invoice, party_amount=900, write_off=1)

			self.assertEqual(
				[(row.account, row.amount) for row in payment.deductions], [("Write Off - _TC", sign * 100)]
			)
			self.assertEqual(get_outstanding(invoice), 0)

	def test_bank_charges_and_tax_withheld_settle_invoice(self):
		bank_charges_account = create_account(
			parent_account="Indirect Expenses - _TC",
			account_name="_Test Bank Charges",
			company="_Test Company",
		)
		tax_withheld_account = create_account(
			parent_account="Current Assets - _TC",
			account_name="_Test TDS Receivable",
			company="_Test Company",
		)
		frappe.db.set_value("Company", "_Test Company", "bank_charges_account", bank_charges_account)
		invoice = create_sales_invoice(rate=1000)

		payment = record(
			invoice,
			party_amount=880,
			bank_charges=20,
			tax_withheld=100,
			tax_withheld_account=tax_withheld_account,
		)

		self.assertEqual(payment.received_amount, 880)
		self.assertEqual(
			{row.account: row.amount for row in payment.deductions},
			{bank_charges_account: 20, tax_withheld_account: 100},
		)
		self.assertEqual(get_outstanding(invoice), 0)

	def test_overpayment_is_kept_as_unapplied_credit(self):
		invoice = create_sales_invoice(rate=1000)
		credit_before = get_unapplied_credit(invoice.doctype, invoice.name)

		payment = record(invoice, party_amount=1200)

		self.assertEqual(payment.unallocated_amount, 200)
		self.assertEqual(get_unapplied_credit(invoice.doctype, invoice.name), credit_before + 200)

	def test_refund_against_credit_note(self):
		credit_note = create_sales_invoice(qty=-1, rate=1000, is_return=1)

		self.assertRaises(frappe.ValidationError, record, credit_note, party_amount=1500)
		payment = record(credit_note, party_amount=400)

		self.assertEqual(payment.payment_type, "Pay")
		self.assertEqual(get_outstanding(credit_note), -600)


def record(*invoices, **values):
	values = {
		"posting_date": nowdate(),
		"account": "_Test Bank - _TC",
		"reference_no": "REF-001",
		"reference_date": nowdate(),
		**values,
	}
	return record_payment(invoices[0].doctype, [invoice.name for invoice in invoices], frappe.as_json(values))


def get_outstanding(invoice):
	return frappe.db.get_value(invoice.doctype, invoice.name, "outstanding_amount")
