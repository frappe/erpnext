import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.report.accounts_payable.accounts_payable import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin


class TestAccountsPayable(AccountsTestMixin, IntegrationTestCase):
	def setUp(self):
		self.create_company()
		self.create_customer()
		self.create_item()
		self.create_supplier(currency="USD", supplier_name="Test Supplier2")
		self.create_usd_payable_account()

	def tearDown(self):
		frappe.db.rollback()

	def test_accounts_payable_for_foreign_currency_supplier(self):
		pi = self.create_purchase_invoice(do_not_submit=True)
		pi.currency = "USD"
		pi.conversion_rate = 80
		pi.credit_to = self.creditors_usd
		pi = pi.save().submit()

		filters = {
			"company": self.company,
			"party_type": "Supplier",
			"party": [self.supplier],
			"report_date": today(),
			"range": "30, 60, 90, 120",
			"in_party_currency": 1,
		}

		data = execute(filters)
		self.assertEqual(data[1][0].get("outstanding"), 300)
		self.assertEqual(data[1][0].get("currency"), "USD")

	def create_purchase_invoice(self, do_not_submit=False):
		frappe.set_user("Administrator")
		pi = make_purchase_invoice(
			item=self.item,
			company=self.company,
			supplier=self.supplier,
			is_return=False,
			update_stock=False,
			posting_date=frappe.utils.datetime.date(2021, 5, 1),
			do_not_save=1,
			rate=300,
			price_list_rate=300,
			qty=1,
		)

		pi = pi.save()
		if not do_not_submit:
			pi = pi.submit()
		return pi

	def test_payment_terms_template_filters(self):
		from erpnext.controllers.accounts_controller import get_payment_terms

		payment_term1 = frappe.get_doc(
			{"doctype": "Payment Term", "payment_term_name": "_Test 50% on 15 Days"}
		).insert()
		payment_term2 = frappe.get_doc(
			{"doctype": "Payment Term", "payment_term_name": "_Test 50% on 30 Days"}
		).insert()

		template = frappe.get_doc(
			{
				"doctype": "Payment Terms Template",
				"template_name": "_Test 50-50",
				"terms": [
					{
						"doctype": "Payment Terms Template Detail",
						"due_date_based_on": "Day(s) after invoice date",
						"payment_term": payment_term1.name,
						"description": "_Test 50-50",
						"invoice_portion": 50,
						"credit_days": 15,
					},
					{
						"doctype": "Payment Terms Template Detail",
						"due_date_based_on": "Day(s) after invoice date",
						"payment_term": payment_term2.name,
						"description": "_Test 50-50",
						"invoice_portion": 50,
						"credit_days": 30,
					},
				],
			}
		)
		template.insert()

		filters = {
			"company": self.company,
			"report_date": today(),
			"range": "30, 60, 90, 120",
			"based_on_payment_terms": 1,
			"payment_terms_template": template.name,
			"ageing_based_on": "Posting Date",
		}

		pi = self.create_purchase_invoice(do_not_submit=True)
		pi.payment_terms_template = template.name
		schedule = get_payment_terms(template.name)
		pi.set("payment_schedule", [])

		for row in schedule:
			row["due_date"] = add_days(pi.posting_date, row.get("credit_days", 0))
			pi.append("payment_schedule", row)

		pi.save()
		pi.submit()

		report = execute(filters)
		row = report[1][0]

		self.assertEqual(len(report[1]), 2)
		self.assertEqual([pi.name, payment_term1.payment_term_name], [row.voucher_no, row.payment_term])
