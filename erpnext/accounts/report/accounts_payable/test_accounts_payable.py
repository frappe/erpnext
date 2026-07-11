import frappe
from frappe.utils import add_days, today

from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.report.accounts_payable.accounts_payable import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.tests.utils import ERPNextTestSuite


class TestAccountsPayable(ERPNextTestSuite, AccountsTestMixin):
	def setUp(self):
		self.company = "_Test Company"
		self.item = "_Test Item"
		self.supplier = "_Test Supplier 2"
		self.creditors_usd = "_Test Payable USD - _TC"

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

	def test_invoice_partially_paid_via_journal_entry(self):
		pi = self.create_purchase_invoice()  # outstanding 300

		je = frappe.new_doc("Journal Entry")
		je.company = self.company
		je.posting_date = today()
		je.append(
			"accounts",
			{
				"account": "Creditors - _TC",
				"party_type": "Supplier",
				"party": self.supplier,
				"debit": 120,
				"debit_in_account_currency": 120,
				"reference_type": "Purchase Invoice",
				"reference_name": pi.name,
				"cost_center": "Main - _TC",
			},
		)
		je.append(
			"accounts",
			{
				"account": "Cash - _TC",
				"credit": 120,
				"credit_in_account_currency": 120,
				"cost_center": "Main - _TC",
			},
		)
		je.save().submit()

		filters = {
			"company": self.company,
			"party_type": "Supplier",
			"party": [self.supplier],
			"report_date": today(),
			"range": "30, 60, 90, 120",
		}
		row = next(row for row in execute(filters)[1] if row.voucher_no == pi.name)
		self.assertEqual(row.paid, 120)
		self.assertEqual(row.outstanding, 180)

	def test_show_remarks_includes_invoice_remark(self):
		pi = self.create_purchase_invoice(do_not_submit=True)
		pi.remarks = "AP test remark"
		pi.save().submit()

		filters = {
			"company": self.company,
			"party_type": "Supplier",
			"party": [self.supplier],
			"report_date": today(),
			"range": "30, 60, 90, 120",
			"show_remarks": 1,
		}
		row = next(row for row in execute(filters)[1] if row.voucher_no == pi.name)
		self.assertIn("AP test remark", row.remarks or "")

	def test_group_by_supplier_totals(self):
		self.create_purchase_invoice()  # outstanding 300

		filters = {
			"company": self.company,
			"party_type": "Supplier",
			"party": [self.supplier],
			"report_date": today(),
			"range": "30, 60, 90, 120",
			"group_by_party": True,
		}
		report = execute(filters)[1]

		# a per-supplier subtotal row plus a grand total row
		party_subtotal = next(
			row for row in report if row.get("party") == self.supplier and not row.get("voucher_no")
		)
		grand_total = next(row for row in report if row.get("party") == "Total")
		self.assertEqual(party_subtotal.get("invoiced"), 300)
		self.assertEqual(grand_total.get("outstanding"), 300)

	def test_payment_terms_template_filters(self):
		from erpnext.controllers.accounts_controller import get_payment_terms

		template = frappe.get_doc("Payment Terms Template", "_Test Payment Term Template")
		first_term = frappe.get_doc("Payment Term", template.terms[0].payment_term)
		expected_payment_term = first_term.description or first_term.name

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
		self.assertEqual([pi.name, expected_payment_term], [row.voucher_no, row.payment_term])

	def test_project_filter(self):
		project = frappe.get_doc("Project", {"project_name": "_Test Project"})

		pi = self.create_purchase_invoice(do_not_submit=True)
		pi.project = project.name
		pi.save().submit()

		filters = {
			"company": self.company,
			"report_date": today(),
			"range": "30, 60, 90, 120",
			"project": [project.name],
		}

		report = execute(filters)[1]
		self.assertEqual(len(report), 1)
		row = report[0]
		self.assertEqual(row.project, project.name)
		self.assertEqual(row.invoiced, 300.0)

	def test_project_on_report_output(self):
		"""
		Report row must carry the invoice's project.
		"""
		filters = {
			"company": self.company,
			"report_date": today(),
			"range": "30, 60, 90, 120",
		}

		project = frappe.get_doc("Project", {"project_name": "_Test Project"})

		pi = self.create_purchase_invoice(do_not_submit=True)
		pi.project = project.name
		pi.save().submit()

		report = execute(filters)

		self.assertEqual(len(report[1]), 1)
		row = report[1][0]
		self.assertEqual([pi.name, project.name, 300], [row.voucher_no, row.project, row.outstanding])
