import frappe
from frappe import qb
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, flt, getdate, today

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.customer_ledger_summary.customer_ledger_summary import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.controllers.sales_and_purchase_return import make_return_doc


class TestCustomerLedgerSummary(AccountsTestMixin, IntegrationTestCase):
	def setUp(self):
		self.create_company()
		self.create_customer()
		self.create_item()
		self.clear_old_entries()

	def tearDown(self):
		frappe.db.rollback()

	def create_sales_invoice(self, do_not_submit=False, **args):
		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			posting_date=today(),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=100,
			qty=10,
			price_list_rate=100,
			do_not_save=1,
			**args,
		)
		si = si.save()
		if not do_not_submit:
			si = si.submit()
		return si

	def create_payment_entry(self, docname, do_not_submit=False):
		pe = get_payment_entry("Sales Invoice", docname, bank_account=self.cash, party_amount=40)
		pe.paid_from = self.debit_to
		pe.insert()
		if not do_not_submit:
			pe.submit()
		return pe

	def create_credit_note(self, docname, do_not_submit=False):
		credit_note = create_sales_invoice(
			company=self.company,
			customer=self.customer,
			item=self.item,
			qty=-1,
			debit_to=self.debit_to,
			cost_center=self.cost_center,
			is_return=1,
			return_against=docname,
			do_not_submit=do_not_submit,
		)

		return credit_note

	def test_ledger_summary_basic_output(self):
		filters = {"company": self.company, "from_date": today(), "to_date": today()}

		si = self.create_sales_invoice(do_not_submit=True)
		si.save().submit()

		expected = {
			"party": "_Test Customer",
			"party_name": "_Test Customer",
			"opening_balance": 0,
			"invoiced_amount": 1000.0,
			"paid_amount": 0,
			"return_amount": 0,
			"closing_balance": 1000.0,
			"currency": "INR",
			"customer_name": "_Test Customer",
		}

		report = execute(filters)[1]
		self.assertEqual(len(report), 1)
		for field in expected:
			with self.subTest(field=field):
				self.assertEqual(report[0].get(field), expected.get(field))

	def test_summary_with_return_and_payment(self):
		filters = {"company": self.company, "from_date": today(), "to_date": today()}

		si = self.create_sales_invoice(do_not_submit=True)
		si.save().submit()

		expected = {
			"party": "_Test Customer",
			"party_name": "_Test Customer",
			"opening_balance": 0,
			"invoiced_amount": 1000.0,
			"paid_amount": 0,
			"return_amount": 0,
			"closing_balance": 1000.0,
			"currency": "INR",
			"customer_name": "_Test Customer",
		}

		report = execute(filters)[1]
		self.assertEqual(len(report), 1)
		for field in expected:
			with self.subTest(field=field):
				self.assertEqual(report[0].get(field), expected.get(field))

		cr_note = self.create_credit_note(si.name, True)
		cr_note.items[0].qty = -2
		cr_note.save().submit()

		expected_after_cr_note = {
			"party": "_Test Customer",
			"party_name": "_Test Customer",
			"opening_balance": 0,
			"invoiced_amount": 1000.0,
			"paid_amount": 0,
			"return_amount": 200.0,
			"closing_balance": 800.0,
			"currency": "INR",
		}
		report = execute(filters)[1]
		self.assertEqual(len(report), 1)
		for field in expected_after_cr_note:
			with self.subTest(field=field):
				self.assertEqual(report[0].get(field), expected_after_cr_note.get(field))

		pe = self.create_payment_entry(si.name, True)
		pe.paid_amount = 500
		pe.save().submit()

		expected_after_cr_and_payment = {
			"party": "_Test Customer",
			"party_name": "_Test Customer",
			"opening_balance": 0,
			"invoiced_amount": 1000.0,
			"paid_amount": 500.0,
			"return_amount": 200.0,
			"closing_balance": 300.0,
			"currency": "INR",
		}

		report = execute(filters)[1]
		self.assertEqual(len(report), 1)
		for field in expected_after_cr_and_payment:
			with self.subTest(field=field):
				self.assertEqual(report[0].get(field), expected_after_cr_and_payment.get(field))

	def test_customer_ledger_ignore_cr_dr_filter(self):
		si = create_sales_invoice()

		cr_note = make_return_doc(si.doctype, si.name)
		cr_note.submit()

		pr = frappe.get_doc("Payment Reconciliation")
		pr.company = si.company
		pr.party_type = "Customer"
		pr.party = si.customer
		pr.receivable_payable_account = si.debit_to

		pr.get_unreconciled_entries()

		invoices = [invoice.as_dict() for invoice in pr.invoices if invoice.invoice_number == si.name]
		payments = [payment.as_dict() for payment in pr.payments if payment.reference_name == cr_note.name]
		pr.allocate_entries(frappe._dict({"invoices": invoices, "payments": payments}))
		pr.reconcile()

		system_generated_journal = frappe.db.get_all(
			"Journal Entry",
			filters={
				"docstatus": 1,
				"reference_type": si.doctype,
				"reference_name": si.name,
				"voucher_type": "Credit Note",
				"is_system_generated": True,
			},
			fields=["name"],
		)
		self.assertEqual(len(system_generated_journal), 1)
		expected = {
			"party": "_Test Customer",
			"customer_name": "_Test Customer",
			"customer_group": "_Test Customer Group",
			"territory": "_Test Territory",
			"party_name": "_Test Customer",
			"opening_balance": 0,
			"invoiced_amount": 100.0,
			"paid_amount": 0.0,
			"return_amount": 100.0,
			"closing_balance": 0.0,
			"currency": "INR",
			"dr_or_cr": "",
		}
		# Without ignore_cr_dr_notes
		columns, data = execute(
			frappe._dict(
				{
					"company": si.company,
					"from_date": si.posting_date,
					"to_date": si.posting_date,
					"ignore_cr_dr_notes": False,
				}
			)
		)
		self.assertEqual(len(data), 1)
		self.assertDictEqual(expected, data[0])

		# With ignore_cr_dr_notes
		expected = {
			"party": "_Test Customer",
			"customer_name": "_Test Customer",
			"customer_group": "_Test Customer Group",
			"territory": "_Test Territory",
			"party_name": "_Test Customer",
			"opening_balance": 0,
			"invoiced_amount": 100.0,
			"paid_amount": 0.0,
			"return_amount": 100.0,
			"closing_balance": 0.0,
			"currency": "INR",
			"dr_or_cr": "",
		}
		columns, data = execute(
			frappe._dict(
				{
					"company": si.company,
					"from_date": si.posting_date,
					"to_date": si.posting_date,
					"ignore_cr_dr_notes": True,
				}
			)
		)
		self.assertEqual(len(data), 1)
		self.assertEqual(expected, data[0])

	def test_journal_voucher_against_return_invoice(self):
		filters = {"company": self.company, "from_date": today(), "to_date": today()}

		# Create Sales Invoice of 10 qty at rate 100 (Amount: 1000.0)
		si1 = self.create_sales_invoice(do_not_submit=True)
		si1.save().submit()

		expected = {
			"party": "_Test Customer",
			"party_name": "_Test Customer",
			"opening_balance": 0,
			"invoiced_amount": 1000.0,
			"paid_amount": 0,
			"return_amount": 0,
			"closing_balance": 1000.0,
			"currency": "INR",
			"customer_name": "_Test Customer",
		}

		report = execute(filters)[1]
		self.assertEqual(len(report), 1)
		for field in expected:
			with self.subTest(field=field):
				actual_value = report[0].get(field)
				expected_value = expected.get(field)
				self.assertEqual(
					actual_value,
					expected_value,
					f"Field {field} does not match expected value. "
					f"Expected: {expected_value}, Got: {actual_value}",
				)

		# Create Payment Entry (Receive) for the first invoice
		pe1 = self.create_payment_entry(si1.name, True)
		pe1.paid_amount = 1000  # Full payment 1000.0
		pe1.save().submit()

		expected_after_payment = {
			"party": "_Test Customer",
			"party_name": "_Test Customer",
			"opening_balance": 0,
			"invoiced_amount": 1000.0,
			"paid_amount": 1000.0,
			"return_amount": 0,
			"closing_balance": 0.0,
			"currency": "INR",
			"customer_name": "_Test Customer",
		}

		report = execute(filters)[1]
		self.assertEqual(len(report), 1)
		for field in expected_after_payment:
			with self.subTest(field=field):
				actual_value = report[0].get(field)
				expected_value = expected_after_payment.get(field)
				self.assertEqual(
					actual_value,
					expected_value,
					f"Field {field} does not match expected value. "
					f"Expected: {expected_value}, Got: {actual_value}",
				)

		# Create Credit Note (return invoice) for first invoice (1000.0)
		cr_note = self.create_credit_note(si1.name, do_not_submit=True)
		cr_note.items[0].qty = -10  # 1 item of qty 10 at rate 100 (Amount: 1000.0)
		cr_note.save().submit()

		expected_after_cr_note = {
			"party": "_Test Customer",
			"party_name": "_Test Customer",
			"opening_balance": 0,
			"invoiced_amount": 1000.0,
			"paid_amount": 1000.0,
			"return_amount": 1000.0,
			"closing_balance": -1000.0,
			"currency": "INR",
			"customer_name": "_Test Customer",
		}

		report = execute(filters)[1]
		self.assertEqual(len(report), 1)
		for field in expected_after_cr_note:
			with self.subTest(field=field):
				actual_value = report[0].get(field)
				expected_value = expected_after_cr_note.get(field)
				self.assertEqual(
					actual_value,
					expected_value,
					f"Field {field} does not match expected value. "
					f"Expected: {expected_value}, Got: {actual_value}",
				)

		# Create Payment Entry for the returned amount (1000.0) - Pay the customer back
		pe2 = get_payment_entry("Sales Invoice", cr_note.name, bank_account=self.cash)
		pe2.insert().submit()

		expected_after_cr_and_return_payment = {
			"party": "_Test Customer",
			"party_name": "_Test Customer",
			"opening_balance": 0,
			"invoiced_amount": 1000.0,
			"paid_amount": 0,
			"return_amount": 1000.0,
			"closing_balance": 0,
			"currency": "INR",
		}

		report = execute(filters)[1]
		self.assertEqual(len(report), 1)
		for field in expected_after_cr_and_return_payment:
			with self.subTest(field=field):
				actual_value = report[0].get(field)
				expected_value = expected_after_cr_and_return_payment.get(field)
				self.assertEqual(
					actual_value,
					expected_value,
					f"Field {field} does not match expected value. "
					f"Expected: {expected_value}, Got: {actual_value}",
				)

		# Create second Sales Invoice of 10 qty at rate 100 (Amount: 1000.0)
		si2 = self.create_sales_invoice(do_not_submit=True)
		si2.save().submit()

		# Create Payment Entry (Receive) for the second invoice - payment (500.0)
		pe3 = self.create_payment_entry(si2.name, True)
		pe3.paid_amount = 500  # Partial payment 500.0
		pe3.save().submit()

		expected_after_cr_and_payment = {
			"party": "_Test Customer",
			"party_name": "_Test Customer",
			"opening_balance": 0.0,
			"invoiced_amount": 2000.0,
			"paid_amount": 500.0,
			"return_amount": 1000.0,
			"closing_balance": 500.0,
			"currency": "INR",
			"customer_name": "_Test Customer",
		}

		report = execute(filters)[1]
		self.assertEqual(len(report), 1)
		for field in expected_after_cr_and_payment:
			with self.subTest(field=field):
				actual_value = report[0].get(field)
				expected_value = expected_after_cr_and_payment.get(field)
				self.assertEqual(
					actual_value,
					expected_value,
					f"Field {field} does not match expected value. "
					f"Expected: {expected_value}, Got: {actual_value}",
				)
