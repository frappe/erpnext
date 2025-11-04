import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin


class TestAccountsReceivable(AccountsTestMixin, IntegrationTestCase):
	def setUp(self):
		self.maxDiff = None
		self.create_company()
		self.create_customer()
		self.create_item()
		self.clear_old_entries()

	def tearDown(self):
		frappe.db.rollback()

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

	@IntegrationTestCase.change_settings("Selling Settings", {"cust_master_name": "Naming Series"})
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
