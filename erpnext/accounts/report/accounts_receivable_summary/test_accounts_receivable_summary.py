import frappe
from frappe.utils import today

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.tests.utils import ERPNextTestSuite


class TestAccountsReceivable(ERPNextTestSuite, AccountsTestMixin):
	def setUp(self):
		self.maxDiff = None
		self.company = "_Test Company"
		self.customer = "_Test Customer"
		self.item = "_Test Item"
		self.debit_to = "Debtors - _TC"
		self.cost_center = "Main - _TC"

	def test_blank_cost_center_gl_balance(self):
		from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
			BLANK_ACCOUNTING_DIMENSION,
		)
		from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
		from erpnext.accounts.report.accounts_payable_summary.accounts_payable_summary import (
			execute as execute_payable,
		)

		for make_invoice, run_report, party_type, party in (
			(create_sales_invoice, execute, "Customer", self.customer),
			(make_purchase_invoice, execute_payable, "Supplier", "_Test Supplier"),
		):
			blank_invoice = make_invoice(qty=1, rate=100, cost_center=self.cost_center)
			named_invoice = make_invoice(qty=1, rate=200, cost_center=self.cost_center)
			for doctype in ("GL Entry", "Payment Ledger Entry"):
				frappe.db.set_value(
					doctype, {"voucher_no": named_invoice.name}, "cost_center", self.cost_center
				)
			parent_cost_center = frappe.db.get_value("Cost Center", self.cost_center, "parent_cost_center")
			filters = frappe._dict(
				company=self.company, report_date=today(), range="30, 60, 90, 120", show_gl_balance=1
			)
			for blank_value in (None, ""):
				for doctype in ("GL Entry", "Payment Ledger Entry"):
					frappe.db.set_value(
						doctype, {"voucher_no": blank_invoice.name}, "cost_center", blank_value
					)
				for selected, expected in (
					([BLANK_ACCOUNTING_DIMENSION], 100),
					([parent_cost_center], 200),
					([BLANK_ACCOUNTING_DIMENSION, parent_cost_center], 300),
				):
					with self.subTest(party_type=party_type, blank_value=blank_value, selected=selected):
						filters.cost_center = selected
						rows = [row for row in run_report(filters.copy())[1] if row.party == party]
						self.assertEqual(len(rows), 1)
						self.assertEqual(rows[0].gl_balance, expected)
						self.assertEqual(rows[0].outstanding, expected)

	def test_01_receivable_summary_output(self):
		"""
		Test for Invoices, Paid, Advance and Outstanding
		"""
		filters = {
			"company": self.company,
			"customer": self.customer,
			"posting_date": today(),
			"range": "30, 60, 90, 120",
		}

		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			posting_date=today(),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=200,
			price_list_rate=200,
		)

		customer_group, customer_territory = frappe.db.get_all(
			"Customer",
			filters={"name": self.customer},
			fields=["customer_group", "territory"],
			as_list=True,
		)[0]

		report = execute(filters)
		rpt_output = report[1]
		expected_data = {
			"party_type": "Customer",
			"advance": 0,
			"party": self.customer,
			"invoiced": 200.0,
			"paid": 0.0,
			"credit_note": 0.0,
			"outstanding": 200.0,
			"range0": 0.0,
			"range1": 200.0,
			"range2": 0.0,
			"range3": 0.0,
			"range4": 0.0,
			"range5": 0.0,
			"total_due": 200.0,
			"future_amount": 0.0,
			"sales_person": [],
			"currency": si.currency,
			"territory": customer_territory,
			"customer_group": customer_group,
		}

		self.assertEqual(len(rpt_output), 1)
		self.assertDictEqual(rpt_output[0], expected_data)

		# simulate advance payment
		pe = get_payment_entry(si.doctype, si.name)
		pe.paid_amount = 50
		pe.references[0].allocated_amount = 0  # this essitially removes the reference
		pe.save().submit()

		# update expected data with advance
		expected_data.update(
			{
				"advance": 50.0,
				"outstanding": 150.0,
				"range1": 150.0,
				"total_due": 150.0,
			}
		)

		report = execute(filters)
		rpt_output = report[1]
		self.assertEqual(len(rpt_output), 1)
		self.assertDictEqual(rpt_output[0], expected_data)

		# make partial payment
		pe = get_payment_entry(si.doctype, si.name)
		pe.paid_amount = 125
		pe.references[0].allocated_amount = 125
		pe.save().submit()

		# update expected data after advance and partial payment
		expected_data.update(
			{"advance": 50.0, "paid": 125.0, "outstanding": 25.0, "range1": 25.0, "total_due": 25.0}
		)

		report = execute(filters)
		rpt_output = report[1]
		self.assertEqual(len(rpt_output), 1)
		self.assertDictEqual(rpt_output[0], expected_data)

	@ERPNextTestSuite.change_settings("Selling Settings", {"cust_master_name": "Naming Series"})
	def test_02_various_filters_and_output(self):
		filters = {
			"company": self.company,
			"customer": self.customer,
			"posting_date": today(),
			"range": "30, 60, 90, 120",
		}

		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			posting_date=today(),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=200,
			price_list_rate=200,
		)
		# make partial payment
		pe = get_payment_entry(si.doctype, si.name)
		pe.paid_amount = 150
		pe.references[0].allocated_amount = 150
		pe.save().submit()

		customer_group, customer_territory = frappe.db.get_all(
			"Customer",
			filters={"name": self.customer},
			fields=["customer_group", "territory"],
			as_list=True,
		)[0]

		report = execute(filters)
		rpt_output = report[1]
		expected_data = {
			"party_type": "Customer",
			"advance": 0,
			"party": self.customer,
			"party_name": self.customer,
			"invoiced": 200.0,
			"paid": 150.0,
			"credit_note": 0.0,
			"outstanding": 50.0,
			"range0": 0.0,
			"range1": 50.0,
			"range2": 0.0,
			"range3": 0.0,
			"range4": 0.0,
			"range5": 0.0,
			"total_due": 50.0,
			"future_amount": 0.0,
			"sales_person": [],
			"currency": si.currency,
			"territory": customer_territory,
			"customer_group": customer_group,
		}

		self.assertEqual(len(rpt_output), 1)
		self.assertDictEqual(rpt_output[0], expected_data)

		# with gl balance filter
		filters.update({"show_gl_balance": True})
		expected_data.update({"gl_balance": 50.0, "diff": 0.0})
		report = execute(filters)
		rpt_output = report[1]
		self.assertEqual(len(rpt_output), 1)
		self.assertDictEqual(rpt_output[0], expected_data)

		# with gl balance and future payments filter
		filters.update({"show_future_payments": True})
		expected_data.update({"remaining_balance": 50.0})
		report = execute(filters)
		rpt_output = report[1]
		self.assertEqual(len(rpt_output), 1)
		self.assertDictEqual(rpt_output[0], expected_data)

		# invoice fully paid
		pe = get_payment_entry(si.doctype, si.name).save().submit()
		report = execute(filters)
		rpt_output = report[1]
		self.assertEqual(len(rpt_output), 0)

	def test_03_summary_sales_partner_column(self):
		partner = "_Test Sales Partner India - 1"

		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			posting_date=today(),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=200,
			price_list_rate=200,
			do_not_submit=True,
		)
		si.sales_partner = partner
		si.save().submit()

		filters = {
			"company": self.company,
			"customer": self.customer,
			"posting_date": today(),
			"range": "30, 60, 90, 120",
			"sales_partner": partner,
		}

		rpt_output = execute(filters)[1]
		self.assertEqual(len(rpt_output), 1)
		self.assertEqual(rpt_output[0].get("sales_partner"), partner)
