import frappe
from frappe.utils import add_days, flt, getdate, today

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.sales_register.sales_register import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.selling.doctype.customer.test_customer import make_customer
from erpnext.selling.doctype.sales_order.test_sales_order import make_sales_order
from erpnext.tests.utils import ERPNextTestSuite


class TestItemWiseSalesRegister(ERPNextTestSuite, AccountsTestMixin):
	def setUp(self):
		self.company = "_Test Company"
		self.customer = "_Test Customer"
		self.item = "_Test Item"
		self.debit_to = "Debtors - _TC"
		self.cost_center = "Main - _TC"
		self.income_account = "Sales - _TC"
		self.cash = "Cash - _TC"
		self.create_child_cost_center()

	def create_child_cost_center(self):
		cc_name = "South Wing"
		if frappe.db.exists("Cost Center", cc_name):
			cc = frappe.get_doc("Cost Center", cc_name)
		else:
			parent = frappe.db.get_value("Cost Center", self.cost_center, "parent_cost_center")
			cc = frappe.get_doc(
				{
					"doctype": "Cost Center",
					"company": self.company,
					"is_group": False,
					"parent_cost_center": parent,
					"cost_center_name": cc_name,
				}
			)
			cc = cc.save()
		self.south_cc = cc.name

	def create_sales_invoice(self, rate=100, do_not_submit=False):
		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			posting_date=today(),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			rate=rate,
			price_list_rate=rate,
			do_not_save=1,
		)
		si = si.save()
		if not do_not_submit:
			si = si.submit()
		return si

	def _ensure_income_account(self, account_name):
		name = f"{account_name} - _TC"
		if not frappe.db.exists("Account", name):
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": account_name,
					"parent_account": "Income - _TC",
					"company": self.company,
					"root_type": "Income",
					"report_type": "Profit and Loss",
					"account_type": "Income Account",
				}
			).insert()
		return name

	def test_income_account_columns_sorted_case_insensitively(self):
		# The dynamic income-account columns must follow MariaDB's case-insensitive collation order and
		# be identical on both engines. Plain python sorted() is case-sensitive (ASCII), so "ZZZ" would
		# sort before "aaa"; casefold restores the pre-effort MariaDB order on both backends.
		lower = self._ensure_income_account("aaa Test Income")
		upper = self._ensure_income_account("ZZZ Test Income")
		for account in (upper, lower):  # submit in non-casefold order
			si = self.create_sales_invoice(do_not_submit=True)
			si.items[0].income_account = account
			si.submit()

		filters = frappe._dict({"from_date": today(), "to_date": today(), "company": self.company})
		columns = execute(filters)[0]
		labels = [col["label"] for col in columns if col.get("label") in (lower, upper)]

		self.assertEqual(labels, sorted([lower, upper], key=str.casefold))

	def test_basic_report_output(self):
		si = self.create_sales_invoice(rate=98)

		filters = frappe._dict({"from_date": today(), "to_date": today(), "company": self.company})
		report = execute(filters)

		self.assertEqual(len(report[1]), 1)

		expected_result = {
			"voucher_type": si.doctype,
			"voucher_no": si.name,
			"posting_date": getdate(),
			"customer": self.customer,
			"receivable_account": self.debit_to,
			"net_total": 98.0,
			"grand_total": 98.0,
			"debit": 98.0,
		}

		report_output = {k: v for k, v in report[1][0].items() if k in expected_result}
		self.assertDictEqual(report_output, expected_result)

	def test_sales_register_ignores_tax_rows_from_other_doctype(self):
		si = self.create_sales_invoice(rate=98)

		# Real workflow setup: create a Sales Order with taxes in the shared child table.
		so = make_sales_order(
			item=self.item,
			company=self.company,
			customer=self.customer,
			rate=77,
			do_not_save=1,
			do_not_submit=1,
		)
		so.append(
			"taxes",
			{
				"charge_type": "Actual",
				"account_head": self.income_account,
				"description": "SO Tax",
				"tax_amount": 55.0,
			},
		)
		so.insert()
		so.submit()

		# Mimic custom naming collision across doctypes (same parent value in shared child table).
		frappe.rename_doc("Sales Order", so.name, si.name, force=True)

		filters = frappe._dict({"from_date": today(), "to_date": today(), "company": self.company})
		report = execute(filters)

		self.assertEqual(len(report[1]), 1)
		result = frappe._dict(report[1][0])
		self.assertEqual(result.voucher_no, si.name)
		self.assertEqual(result.net_total, 98.0)
		self.assertEqual(result.tax_total, 0)
		self.assertEqual(result.grand_total, 98.0)

	def test_journal_with_cost_center_filter(self):
		je1 = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"company": self.company,
				"posting_date": getdate(),
				"accounts": [
					{
						"account": self.debit_to,
						"party_type": "Customer",
						"party": self.customer,
						"credit_in_account_currency": 77,
						"credit": 77,
						"is_advance": "Yes",
						"cost_center": self.cost_center,
					},
					{
						"account": self.cash,
						"debit_in_account_currency": 77,
						"debit": 77,
					},
				],
			}
		)
		je1.submit()

		je2 = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"company": self.company,
				"posting_date": getdate(),
				"accounts": [
					{
						"account": self.debit_to,
						"party_type": "Customer",
						"party": self.customer,
						"credit_in_account_currency": 98,
						"credit": 98,
						"is_advance": "Yes",
						"cost_center": self.south_cc,
					},
					{
						"account": self.cash,
						"debit_in_account_currency": 98,
						"debit": 98,
					},
				],
			}
		)
		je2.submit()

		filters = frappe._dict(
			{
				"from_date": today(),
				"to_date": today(),
				"company": self.company,
				"include_payments": True,
				"customer": self.customer,
				"cost_center": self.cost_center,
			}
		)
		report_output = execute(filters)[1]
		filtered_output = [x for x in report_output if x.get("voucher_no") == je1.name]
		self.assertEqual(len(filtered_output), 1)
		expected_result = {
			"voucher_type": je1.doctype,
			"voucher_no": je1.name,
			"posting_date": je1.posting_date,
			"customer": self.customer,
			"receivable_account": self.debit_to,
			"net_total": 77.0,
			"credit": 77.0,
		}
		result_fields = {k: v for k, v in filtered_output[0].items() if k in expected_result}
		self.assertDictEqual(result_fields, expected_result)

		filters = frappe._dict(
			{
				"from_date": today(),
				"to_date": today(),
				"company": self.company,
				"include_payments": True,
				"customer": self.customer,
				"cost_center": self.south_cc,
			}
		)
		report_output = execute(filters)[1]
		filtered_output = [x for x in report_output if x.get("voucher_no") == je2.name]
		self.assertEqual(len(filtered_output), 1)
		expected_result = {
			"voucher_type": je2.doctype,
			"voucher_no": je2.name,
			"posting_date": je2.posting_date,
			"customer": self.customer,
			"receivable_account": self.debit_to,
			"net_total": 98.0,
			"credit": 98.0,
		}
		result_output = {k: v for k, v in filtered_output[0].items() if k in expected_result}
		self.assertDictEqual(result_output, expected_result)

	def test_outstanding_currency_conversion(self):
		foreign_invoice = create_sales_invoice(
			customer="_Test Customer",
			posting_date=add_days(today(), -1),
			qty=1,
			rate=100,
		)
		foreign_invoice.db_set("currency", "USD")
		foreign_invoice.db_set("conversion_rate", 80)
		foreign_invoice.db_set("outstanding_amount", 100.236)
		make_customer("_Test Customer2")
		local_invoice = create_sales_invoice(
			customer="_Test Customer2", currency="INR", conversion_rate=1, qty=1, rate=200
		)
		local_invoice.db_set("outstanding_amount", 200.456)
		columns, data, *_ = execute(frappe._dict({"company": foreign_invoice.company}))
		outstanding_precision = 2

		data_by_name = {x.get("voucher_no"): x.get("outstanding_amount") for x in data}
		self.assertEqual(data_by_name.get(foreign_invoice.name), flt((100.236 * 80), outstanding_precision))
		self.assertEqual(data_by_name.get(local_invoice.name), flt(200.456, outstanding_precision))
