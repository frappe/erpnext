import unittest

import frappe
from frappe import qb
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_days, flt, getdate, today

from erpnext import get_default_cost_center
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.accounts_receivable.accounts_receivable import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order


class TestAccountsReceivable(AccountsTestMixin, FrappeTestCase):
	def setUp(self):
		self.create_company()
		self.create_customer()
		self.create_item()
		self.create_usd_receivable_account()
		self.clear_old_entries()

	def tearDown(self):
		frappe.db.rollback()

	def create_sales_invoice(self, no_payment_schedule=False, do_not_submit=False):
		frappe.set_user("Administrator")
		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			posting_date=today(),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=100,
			price_list_rate=100,
			do_not_save=1,
		)
		if not no_payment_schedule:
			si.append(
				"payment_schedule",
				dict(due_date=getdate(add_days(today(), 30)), invoice_portion=30.00, payment_amount=30),
			)
			si.append(
				"payment_schedule",
				dict(due_date=getdate(add_days(today(), 60)), invoice_portion=50.00, payment_amount=50),
			)
			si.append(
				"payment_schedule",
				dict(due_date=getdate(add_days(today(), 90)), invoice_portion=20.00, payment_amount=20),
			)
		si = si.save()
		if not do_not_submit:
			si = si.submit()
		return si

	def create_payment_entry(self, docname):
		pe = get_payment_entry("Sales Invoice", docname, bank_account=self.cash, party_amount=40)
		pe.paid_from = self.debit_to
		pe.insert()
		pe.submit()

	def create_credit_note(self, docname):
		credit_note = create_sales_invoice(
			company=self.company,
			customer=self.customer,
			item=self.item,
			qty=-1,
			debit_to=self.debit_to,
			cost_center=self.cost_center,
			is_return=1,
			return_against=docname,
		)

		return credit_note

	def test_accounts_receivable(self):
		filters = {
			"company": self.company,
			"based_on_payment_terms": 1,
			"report_date": today(),
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
			"show_remarks": True,
		}

		# check invoice grand total and invoiced column's value for 3 payment terms
		si = self.create_sales_invoice()
		name = si.name

		report = execute(filters)

		expected_data = [[100, 30, "No Remarks"], [100, 50, "No Remarks"], [100, 20, "No Remarks"]]

		for i in range(3):
			row = report[1][i - 1]
			self.assertEqual(expected_data[i - 1], [row.invoice_grand_total, row.invoiced, row.remarks])

		# check invoice grand total, invoiced, paid and outstanding column's value after payment
		self.create_payment_entry(si.name)
		report = execute(filters)

		expected_data_after_payment = [[100, 50, 10, 40], [100, 20, 0, 20]]

		for i in range(2):
			row = report[1][i - 1]
			self.assertEqual(
				expected_data_after_payment[i - 1],
				[row.invoice_grand_total, row.invoiced, row.paid, row.outstanding],
			)

		# check invoice grand total, invoiced, paid and outstanding column's value after credit note
		self.create_credit_note(si.name)
		report = execute(filters)

		expected_data_after_credit_note = [100, 0, 0, 40, -40, self.debit_to]

		row = report[1][0]
		self.assertEqual(
			expected_data_after_credit_note,
			[
				row.invoice_grand_total,
				row.invoiced,
				row.paid,
				row.credit_note,
				row.outstanding,
				row.party_account,
			],
		)

	def test_payment_againt_po_in_receivable_report(self):
		"""
		Payments made against Purchase Order will show up as outstanding amount
		"""

		so = make_sales_order(
			company=self.company,
			customer=self.customer,
			warehouse=self.warehouse,
			debit_to=self.debit_to,
			income_account=self.income_account,
			expense_account=self.expense_account,
			cost_center=self.cost_center,
		)

		pe = get_payment_entry(so.doctype, so.name)
		pe = pe.save().submit()

		filters = {
			"company": self.company,
			"based_on_payment_terms": 0,
			"report_date": today(),
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
		}

		report = execute(filters)

		expected_data_after_payment = [0, 1000, 0, -1000]

		row = report[1][0]
		self.assertEqual(
			expected_data_after_payment,
			[
				row.invoiced,
				row.paid,
				row.credit_note,
				row.outstanding,
			],
		)

	@change_settings(
		"Accounts Settings",
		{"allow_multi_currency_invoices_against_single_party_account": 1, "allow_stale": 0},
	)
	def test_exchange_revaluation_for_party(self):
		"""
		Exchange Revaluation for party on Receivable/Payable should be included
		"""

		# Using Exchange Gain/Loss account for unrealized as well.
		company_doc = frappe.get_doc("Company", self.company)
		company_doc.unrealized_exchange_gain_loss_account = company_doc.exchange_gain_loss_account
		company_doc.save()

		si = self.create_sales_invoice(no_payment_schedule=True, do_not_submit=True)
		si.currency = "USD"
		si.conversion_rate = 80
		si.debit_to = self.debtors_usd
		si = si.save().submit()

		# Exchange Revaluation
		err = frappe.new_doc("Exchange Rate Revaluation")
		err.company = self.company
		err.posting_date = today()
		accounts = err.get_accounts_data()
		err.extend("accounts", accounts)
		err.accounts[0].new_exchange_rate = 85
		row = err.accounts[0]
		row.new_balance_in_base_currency = flt(
			row.new_exchange_rate * flt(row.balance_in_account_currency)
		)
		row.gain_loss = row.new_balance_in_base_currency - flt(row.balance_in_base_currency)
		err.set_total_gain_loss()
		err = err.save().submit()

		# Submit JV for ERR
		err_journals = err.make_jv_entries()
		je = frappe.get_doc("Journal Entry", err_journals.get("revaluation_jv"))
		je = je.submit()

		filters = {
			"company": self.company,
			"report_date": today(),
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
		}
		report = execute(filters)

		expected_data_for_err = [0, -500, 0, 500]
		row = [x for x in report[1] if x.voucher_type == je.doctype and x.voucher_no == je.name][0]
		self.assertEqual(
			expected_data_for_err,
			[
				row.invoiced,
				row.paid,
				row.credit_note,
				row.outstanding,
			],
		)

	def test_payment_against_credit_note(self):
		"""
		Payment against credit/debit note should be considered against the parent invoice
		"""

		si1 = self.create_sales_invoice()

		pe = get_payment_entry(si1.doctype, si1.name, bank_account=self.cash)
		pe.paid_from = self.debit_to
		pe.insert()
		pe.submit()

		cr_note = self.create_credit_note(si1.name)

		si2 = self.create_sales_invoice()

		# manually link cr_note with si2 using journal entry
		je = frappe.new_doc("Journal Entry")
		je.company = self.company
		je.voucher_type = "Credit Note"
		je.posting_date = today()

		debit_entry = {
			"account": self.debit_to,
			"party_type": "Customer",
			"party": self.customer,
			"debit": 100,
			"debit_in_account_currency": 100,
			"reference_type": cr_note.doctype,
			"reference_name": cr_note.name,
			"cost_center": self.cost_center,
		}
		credit_entry = {
			"account": self.debit_to,
			"party_type": "Customer",
			"party": self.customer,
			"credit": 100,
			"credit_in_account_currency": 100,
			"reference_type": si2.doctype,
			"reference_name": si2.name,
			"cost_center": self.cost_center,
		}

		je.append("accounts", debit_entry)
		je.append("accounts", credit_entry)
		je = je.save().submit()

		filters = {
			"company": self.company,
			"report_date": today(),
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
		}
		report = execute(filters)
		self.assertEqual(report[1], [])

	def test_group_by_party(self):
		si1 = self.create_sales_invoice(do_not_submit=True)
		si1.posting_date = add_days(today(), -1)
		si1.save().submit()
		si2 = self.create_sales_invoice(do_not_submit=True)
		si2.items[0].rate = 85
		si2.save().submit()

		filters = {
			"company": self.company,
			"report_date": today(),
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
			"group_by_party": True,
		}
		report = execute(filters)[1]
		self.assertEqual(len(report), 5)

		# assert voucher rows
		expected_voucher_rows = [
			[100.0, 100.0, 100.0, 100.0],
			[85.0, 85.0, 85.0, 85.0],
		]
		voucher_rows = []
		for x in report[0:2]:
			voucher_rows.append(
				[x.invoiced, x.outstanding, x.invoiced_in_account_currency, x.outstanding_in_account_currency]
			)
		self.assertEqual(expected_voucher_rows, voucher_rows)

		# assert total rows
		expected_total_rows = [
			[self.customer, 185.0, 185.0],  # party total
			{},  # empty row for padding
			["Total", 185.0, 185.0],  # grand total
		]
		party_total_row = report[2]
		self.assertEqual(
			expected_total_rows[0],
			[
				party_total_row.get("party"),
				party_total_row.get("invoiced"),
				party_total_row.get("outstanding"),
			],
		)
		empty_row = report[3]
		self.assertEqual(expected_total_rows[1], empty_row)
		grand_total_row = report[4]
		self.assertEqual(
			expected_total_rows[2],
			[
				grand_total_row.get("party"),
				grand_total_row.get("invoiced"),
				grand_total_row.get("outstanding"),
			],
		)

	def test_future_payments(self):
		si = self.create_sales_invoice()
		pe = get_payment_entry(si.doctype, si.name)
		pe.posting_date = add_days(today(), 1)
		pe.paid_amount = 90.0
		pe.references[0].allocated_amount = 90.0
		pe.save().submit()
		filters = {
			"company": self.company,
			"report_date": today(),
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
			"show_future_payments": True,
		}
		report = execute(filters)[1]
		self.assertEqual(len(report), 1)

		expected_data = [100.0, 100.0, 10.0, 90.0]

		row = report[0]
		self.assertEqual(
			expected_data, [row.invoiced, row.outstanding, row.remaining_balance, row.future_amount]
		)

		pe.cancel()
		# full payment in future date
		pe = get_payment_entry(si.doctype, si.name)
		pe.posting_date = add_days(today(), 1)
		pe.save().submit()
		report = execute(filters)[1]
		self.assertEqual(len(report), 1)
		expected_data = [100.0, 100.0, 0.0, 100.0]
		row = report[0]
		self.assertEqual(
			expected_data, [row.invoiced, row.outstanding, row.remaining_balance, row.future_amount]
		)

		pe.cancel()
		# over payment in future date
		pe = get_payment_entry(si.doctype, si.name)
		pe.posting_date = add_days(today(), 1)
		pe.paid_amount = 110
		pe.save().submit()
		report = execute(filters)[1]
		self.assertEqual(len(report), 2)
		expected_data = [[100.0, 0.0, 100.0, 0.0, 100.0], [0.0, 10.0, -10.0, -10.0, 0.0]]
		for idx, row in enumerate(report):
			self.assertEqual(
				expected_data[idx],
				[row.invoiced, row.paid, row.outstanding, row.remaining_balance, row.future_amount],
			)

	def test_sales_person(self):
		sales_person = (
			frappe.get_doc({"doctype": "Sales Person", "sales_person_name": "John Clark", "enabled": True})
			.insert()
			.submit()
		)
		si = self.create_sales_invoice(do_not_submit=True)
		si.append("sales_team", {"sales_person": sales_person.name, "allocated_percentage": 100})
		si.save().submit()

		filters = {
			"company": self.company,
			"report_date": today(),
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
			"sales_person": sales_person.name,
			"show_sales_person": True,
		}
		report = execute(filters)[1]
		self.assertEqual(len(report), 1)

		expected_data = [100.0, 100.0, sales_person.name]

		row = report[0]
		self.assertEqual(expected_data, [row.invoiced, row.outstanding, row.sales_person])

	def test_cost_center_filter(self):
		si = self.create_sales_invoice()
		filters = {
			"company": self.company,
			"report_date": today(),
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
			"cost_center": self.cost_center,
		}
		report = execute(filters)[1]
		self.assertEqual(len(report), 1)
		expected_data = [100.0, 100.0, self.cost_center]
		row = report[0]
		self.assertEqual(expected_data, [row.invoiced, row.outstanding, row.cost_center])

	def test_customer_group_filter(self):
		si = self.create_sales_invoice()
		cus_group = frappe.db.get_value("Customer", self.customer, "customer_group")
		filters = {
			"company": self.company,
			"report_date": today(),
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
			"customer_group": cus_group,
		}
		report = execute(filters)[1]
		self.assertEqual(len(report), 1)
		expected_data = [100.0, 100.0, cus_group]
		row = report[0]
		self.assertEqual(expected_data, [row.invoiced, row.outstanding, row.customer_group])

		filters.update({"customer_group": "Individual"})
		report = execute(filters)[1]
		self.assertEqual(len(report), 0)

	def test_multi_customer_group_filter(self):
		si = self.create_sales_invoice()
		cus_group = frappe.db.get_value("Customer", self.customer, "customer_group")
		# Create a list of customer groups, e.g., ["Group1", "Group2"]
		cus_groups_list = [cus_group, "_Test Customer Group 1"]

		filters = {
			"company": self.company,
			"report_date": today(),
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
			"customer_group": cus_groups_list,  # Use the list of customer groups
		}
		report = execute(filters)[1]

		# Assert that the report contains data for the specified customer groups
		self.assertTrue(len(report) > 0)

		for row in report:
			# Assert that the customer group of each row is in the list of customer groups
			self.assertIn(row.customer_group, cus_groups_list)

	def test_party_account_filter(self):
		si1 = self.create_sales_invoice()
		self.customer2 = (
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": "Jane Doe",
					"type": "Individual",
					"default_currency": "USD",
				}
			)
			.insert()
			.submit()
		)

		si2 = self.create_sales_invoice(do_not_submit=True)
		si2.posting_date = add_days(today(), -1)
		si2.customer = self.customer2
		si2.currency = "USD"
		si2.conversion_rate = 80
		si2.debit_to = self.debtors_usd
		si2.save().submit()

		# Filter on company currency receivable account
		filters = {
			"company": self.company,
			"report_date": today(),
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
			"party_account": self.debit_to,
		}
		report = execute(filters)[1]
		self.assertEqual(len(report), 1)
		expected_data = [100.0, 100.0, self.debit_to, si1.currency]
		row = report[0]
		self.assertEqual(
			expected_data, [row.invoiced, row.outstanding, row.party_account, row.account_currency]
		)

		# Filter on USD receivable account
		filters.update({"party_account": self.debtors_usd})
		report = execute(filters)[1]
		self.assertEqual(len(report), 1)
		expected_data = [8000.0, 8000.0, self.debtors_usd, si2.currency]
		row = report[0]
		self.assertEqual(
			expected_data, [row.invoiced, row.outstanding, row.party_account, row.account_currency]
		)

		# without filter on party account
		filters.pop("party_account")
		report = execute(filters)[1]
		self.assertEqual(len(report), 2)
		expected_data = [
			[8000.0, 8000.0, 100.0, 100.0, self.debtors_usd, si2.currency],
			[100.0, 100.0, 100.0, 100.0, self.debit_to, si1.currency],
		]
		for idx, row in enumerate(report):
			self.assertEqual(
				expected_data[idx],
				[
					row.invoiced,
					row.outstanding,
					row.invoiced_in_account_currency,
					row.outstanding_in_account_currency,
					row.party_account,
					row.account_currency,
				],
			)

	def test_usd_customer_filter(self):
		filters = {
			"company": self.company,
			"party_type": "Customer",
			"party": [self.customer],
			"report_date": today(),
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
		}

		si = self.create_sales_invoice(no_payment_schedule=True, do_not_submit=True)
		si.currency = "USD"
		si.conversion_rate = 80
		si.debit_to = self.debtors_usd
		si.save().submit()
		name = si.name

		# check invoice grand total and invoiced column's value for 3 payment terms
		report = execute(filters)

		expected = {
			"voucher_type": si.doctype,
			"voucher_no": si.name,
			"party_account": self.debtors_usd,
			"customer_name": self.customer,
			"invoiced": 100.0,
			"outstanding": 100.0,
			"account_currency": "USD",
		}
		self.assertEqual(len(report[1]), 1)
		report_output = report[1][0]
		for field in expected:
			with self.subTest(field=field):
				self.assertEqual(report_output.get(field), expected.get(field))

	def test_multi_select_party_filter(self):
		self.customer1 = self.customer
		self.create_customer("_Test Customer 2")
		self.customer2 = self.customer
		self.create_customer("_Test Customer 3")
		self.customer3 = self.customer

		filters = {
			"company": self.company,
			"party_type": "Customer",
			"party": [self.customer1, self.customer3],
			"report_date": today(),
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
		}

		si1 = self.create_sales_invoice(no_payment_schedule=True, do_not_submit=True)
		si1.customer = self.customer1
		si1.save().submit()

		si2 = self.create_sales_invoice(no_payment_schedule=True, do_not_submit=True)
		si2.customer = self.customer2
		si2.save().submit()

		si3 = self.create_sales_invoice(no_payment_schedule=True, do_not_submit=True)
		si3.customer = self.customer3
		si3.save().submit()

		# check invoice grand total and invoiced column's value for 3 payment terms
		report = execute(filters)

		expected_output = {self.customer1, self.customer3}
		self.assertEqual(len(report[1]), 2)
		output_for = set([x.party for x in report[1]])
		self.assertEqual(output_for, expected_output)

	def test_report_output_if_party_is_missing(self):
		acc_name = "Additional Debtors"
		if not frappe.db.get_value(
			"Account", filters={"account_name": acc_name, "company": self.company}
		):
			additional_receivable_acc = frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": acc_name,
					"parent_account": "Accounts Receivable - " + self.company_abbr,
					"company": self.company,
					"account_type": "Receivable",
				}
			).save()
			self.debtors2 = additional_receivable_acc.name

		je = frappe.new_doc("Journal Entry")
		je.company = self.company
		je.posting_date = today()
		je.append(
			"accounts",
			{
				"account": self.debit_to,
				"party_type": "Customer",
				"party": self.customer,
				"debit_in_account_currency": 150,
				"credit_in_account_currency": 0,
				"cost_center": self.cost_center,
			},
		)
		je.append(
			"accounts",
			{
				"account": self.debtors2,
				"party_type": "Customer",
				"party": self.customer,
				"debit_in_account_currency": 200,
				"credit_in_account_currency": 0,
				"cost_center": self.cost_center,
			},
		)
		je.append(
			"accounts",
			{
				"account": self.cash,
				"debit_in_account_currency": 0,
				"credit_in_account_currency": 350,
				"cost_center": self.cost_center,
			},
		)
		je.save().submit()

		# manually remove party from Payment Ledger
		ple = qb.DocType("Payment Ledger Entry")
		qb.update(ple).set(ple.party, None).where(ple.voucher_no == je.name).run()

		filters = {
			"company": self.company,
			"report_date": today(),
			"range1": 30,
			"range2": 60,
			"range3": 90,
			"range4": 120,
		}

		report_ouput = execute(filters)[1]
		expected_data = [
			[self.debtors2, je.doctype, je.name, "Customer", self.customer, 200.0, 0.0, 0.0, 200.0],
			[self.debit_to, je.doctype, je.name, "Customer", self.customer, 150.0, 0.0, 0.0, 150.0],
		]
		self.assertEqual(len(report_ouput), 2)
		# fetch only required fields
		report_output = [
			[
				x.party_account,
				x.voucher_type,
				x.voucher_no,
				"Customer",
				self.customer,
				x.invoiced,
				x.paid,
				x.credit_note,
				x.outstanding,
			]
			for x in report_ouput
		]
		# use account name to sort
		# post sorting output should be [[Additional Debtors, ...], [Debtors, ...]]
		report_output = sorted(report_output, key=lambda x: x[0])
		self.assertEqual(expected_data, report_output)
