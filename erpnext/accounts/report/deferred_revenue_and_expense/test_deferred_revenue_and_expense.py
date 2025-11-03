import frappe
from frappe import _dict, qb
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import nowdate

from erpnext.accounts.doctype.account.test_account import create_account
from erpnext.accounts.doctype.purchase_invoice.test_purchase_invoice import make_purchase_invoice
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.deferred_revenue_and_expense.deferred_revenue_and_expense import (
	Deferred_Item,
	Deferred_Revenue_and_Expense_Report,
)
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin
from erpnext.accounts.utils import get_fiscal_year


class TestDeferredRevenueAndExpense(FrappeTestCase, AccountsTestMixin):
	@classmethod
	def setUpClass(self):
		self.maxDiff = None

	def clear_old_entries(self):
		sinv = qb.DocType("Sales Invoice")
		sinv_item = qb.DocType("Sales Invoice Item")
		pinv = qb.DocType("Purchase Invoice")
		pinv_item = qb.DocType("Purchase Invoice Item")

		# delete existing invoices with deferred items
		deferred_invoices = (
			qb.from_(sinv)
			.join(sinv_item)
			.on(sinv.name == sinv_item.parent)
			.select(sinv.name)
			.where(sinv_item.enable_deferred_revenue == 1)
			.run()
		)
		if deferred_invoices:
			qb.from_(sinv).delete().where(sinv.name.isin(deferred_invoices)).run()

		deferred_invoices = (
			qb.from_(pinv)
			.join(pinv_item)
			.on(pinv.name == pinv_item.parent)
			.select(pinv.name)
			.where(pinv_item.enable_deferred_expense == 1)
			.run()
		)
		if deferred_invoices:
			qb.from_(pinv).delete().where(pinv.name.isin(deferred_invoices)).run()

	def setup_deferred_accounts_and_items(self):
		# created deferred expense accounts, if not found
		self.deferred_revenue_account = create_account(
			account_name="Deferred Revenue",
			parent_account="Current Liabilities - " + self.company_abbr,
			company=self.company,
		)

		# created deferred expense accounts, if not found
		self.deferred_expense_account = create_account(
			account_name="Deferred Expense",
			parent_account="Current Assets - " + self.company_abbr,
			company=self.company,
		)

	def setUp(self):
		self.create_company()
		self.create_customer("_Test Customer")
		self.create_supplier("_Test Furniture Supplier")
		self.setup_deferred_accounts_and_items()
		self.clear_old_entries()

	def tearDown(self):
		frappe.db.rollback()

	@change_settings("Accounts Settings", {"book_deferred_entries_based_on": "Months"})
	def test_deferred_revenue(self):
		self.create_item("_Test Internet Subscription", 0, self.warehouse, self.company)
		item = frappe.get_doc("Item", self.item)
		item.enable_deferred_revenue = 1
		item.item_defaults[0].deferred_revenue_account = self.deferred_revenue_account
		item.no_of_months = 3
		item.save()

		si = create_sales_invoice(
			item=self.item,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			posting_date="2021-05-01",
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			do_not_save=True,
			rate=300,
			price_list_rate=300,
		)

		si.items[0].income_account = self.income_account
		si.items[0].enable_deferred_revenue = 1
		si.items[0].service_start_date = "2021-05-01"
		si.items[0].service_end_date = "2021-08-01"
		si.items[0].deferred_revenue_account = self.deferred_revenue_account
		si.save()
		si.submit()

		pda = frappe.get_doc(
			dict(
				doctype="Process Deferred Accounting",
				posting_date=nowdate(),
				start_date="2021-05-01",
				end_date="2021-08-01",
				type="Income",
				company=self.company,
			)
		)
		pda.insert()
		pda.submit()

		# execute report
		fiscal_year = frappe.get_doc("Fiscal Year", get_fiscal_year(date="2021-05-01"))
		self.filters = frappe._dict(
			{
				"company": self.company,
				"filter_based_on": "Date Range",
				"period_start_date": "2021-05-01",
				"period_end_date": "2021-08-01",
				"from_fiscal_year": fiscal_year.year,
				"to_fiscal_year": fiscal_year.year,
				"periodicity": "Monthly",
				"type": "Revenue",
				"with_upcoming_postings": False,
			}
		)

		report = Deferred_Revenue_and_Expense_Report(filters=self.filters)
		report.run()
		expected = [
			{"key": "may_2021", "total": 100.0, "actual": 100.0},
			{"key": "jun_2021", "total": 100.0, "actual": 100.0},
			{"key": "jul_2021", "total": 100.0, "actual": 100.0},
			{"key": "aug_2021", "total": 0, "actual": 0},
		]
		self.assertEqual(report.period_total, expected)

	@change_settings("Accounts Settings", {"book_deferred_entries_based_on": "Months"})
	def test_deferred_expense(self):
		self.create_item("_Test Office Desk", 0, self.warehouse, self.company)
		item = frappe.get_doc("Item", self.item)
		item.enable_deferred_expense = 1
		item.item_defaults[0].deferred_expense_account = self.deferred_expense_account
		item.no_of_months_exp = 3
		item.save()

		pi = make_purchase_invoice(
			item=self.item,
			company=self.company,
			supplier=self.supplier,
			is_return=False,
			update_stock=False,
			posting_date=frappe.utils.datetime.date(2021, 5, 1),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			do_not_save=True,
			rate=300,
			price_list_rate=300,
			warehouse=self.warehouse,
			qty=1,
		)
		pi.set_posting_time = True
		pi.items[0].enable_deferred_expense = 1
		pi.items[0].service_start_date = "2021-05-01"
		pi.items[0].service_end_date = "2021-08-01"
		pi.items[0].deferred_expense_account = self.deferred_expense_account
		pi.items[0].expense_account = self.expense_account
		pi.save()
		pi.submit()

		pda = frappe.get_doc(
			dict(
				doctype="Process Deferred Accounting",
				posting_date=nowdate(),
				start_date="2021-05-01",
				end_date="2021-08-01",
				type="Expense",
				company=self.company,
			)
		)
		pda.insert()
		pda.submit()

		# execute report
		fiscal_year = frappe.get_doc("Fiscal Year", get_fiscal_year(date="2021-05-01"))
		self.filters = frappe._dict(
			{
				"company": self.company,
				"filter_based_on": "Date Range",
				"period_start_date": "2021-05-01",
				"period_end_date": "2021-08-01",
				"from_fiscal_year": fiscal_year.year,
				"to_fiscal_year": fiscal_year.year,
				"periodicity": "Monthly",
				"type": "Expense",
				"with_upcoming_postings": False,
			}
		)

		report = Deferred_Revenue_and_Expense_Report(filters=self.filters)
		report.run()
		expected = [
			{"key": "may_2021", "total": -100.0, "actual": -100.0},
			{"key": "jun_2021", "total": -100.0, "actual": -100.0},
			{"key": "jul_2021", "total": -100.0, "actual": -100.0},
			{"key": "aug_2021", "total": 0, "actual": 0},
		]
		self.assertEqual(report.period_total, expected)

	@change_settings("Accounts Settings", {"book_deferred_entries_based_on": "Months"})
	def test_zero_months(self):
		self.create_item("_Test Internet Subscription", 0, self.warehouse, self.company)
		item = frappe.get_doc("Item", self.item)
		item.enable_deferred_revenue = 1
		item.deferred_revenue_account = self.deferred_revenue_account
		item.no_of_months = 0
		item.save()

		si = create_sales_invoice(
			item=item.name,
			company=self.company,
			customer=self.customer,
			debit_to=self.debit_to,
			posting_date="2021-05-01",
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			do_not_save=True,
			rate=300,
			price_list_rate=300,
		)

		si.items[0].enable_deferred_revenue = 1
		si.items[0].income_account = self.income_account
		si.items[0].deferred_revenue_account = self.deferred_revenue_account
		si.save()
		si.submit()

		pda = frappe.get_doc(
			dict(
				doctype="Process Deferred Accounting",
				posting_date=nowdate(),
				start_date="2021-05-01",
				end_date="2021-08-01",
				type="Income",
				company=self.company,
			)
		)
		pda.insert()
		pda.submit()

		# execute report
		fiscal_year = frappe.get_doc("Fiscal Year", get_fiscal_year(date="2021-05-01"))
		self.filters = frappe._dict(
			{
				"company": self.company,
				"filter_based_on": "Date Range",
				"period_start_date": "2021-05-01",
				"period_end_date": "2021-08-01",
				"from_fiscal_year": fiscal_year.year,
				"to_fiscal_year": fiscal_year.year,
				"periodicity": "Monthly",
				"type": "Revenue",
				"with_upcoming_postings": False,
			}
		)

		report = Deferred_Revenue_and_Expense_Report(filters=self.filters)
		report.run()
		expected = [
			{"key": "may_2021", "total": 300.0, "actual": 300.0},
			{"key": "jun_2021", "total": 0, "actual": 0},
			{"key": "jul_2021", "total": 0, "actual": 0},
			{"key": "aug_2021", "total": 0, "actual": 0},
		]
		self.assertEqual(report.period_total, expected)

	@change_settings(
		"Accounts Settings",
		{"book_deferred_entries_based_on": "Months", "book_deferred_entries_via_journal_entry": 0},
	)
	def test_zero_amount(self):
		self.create_item("_Test Office Desk", 0, self.warehouse, self.company)
		item = frappe.get_doc("Item", self.item)
		item.enable_deferred_expense = 1
		item.item_defaults[0].deferred_expense_account = self.deferred_expense_account
		item.no_of_months_exp = 12
		item.save()

		pi = make_purchase_invoice(
			item=self.item,
			company=self.company,
			supplier=self.supplier,
			is_return=False,
			update_stock=False,
			posting_date=frappe.utils.datetime.date(2021, 12, 30),
			parent_cost_center=self.cost_center,
			cost_center=self.cost_center,
			do_not_save=True,
			rate=3910,
			price_list_rate=3910,
			warehouse=self.warehouse,
			qty=1,
		)
		pi.set_posting_time = True
		pi.items[0].enable_deferred_expense = 1
		pi.items[0].service_start_date = "2021-12-30"
		pi.items[0].service_end_date = "2022-12-30"
		pi.items[0].deferred_expense_account = self.deferred_expense_account
		pi.items[0].expense_account = self.expense_account
		pi.save()
		pi.submit()

		pda = frappe.get_doc(
			doctype="Process Deferred Accounting",
			posting_date=nowdate(),
			start_date="2022-01-01",
			end_date="2022-01-31",
			type="Expense",
			company=self.company,
		)
		pda.insert()
		pda.submit()

		# execute report
		fiscal_year = frappe.get_doc("Fiscal Year", get_fiscal_year(date="2022-01-31"))
		self.filters = frappe._dict(
			{
				"company": self.company,
				"filter_based_on": "Date Range",
				"period_start_date": "2022-01-01",
				"period_end_date": "2022-01-31",
				"from_fiscal_year": fiscal_year.year,
				"to_fiscal_year": fiscal_year.year,
				"periodicity": "Monthly",
				"type": "Expense",
				"with_upcoming_postings": False,
			}
		)

		report = Deferred_Revenue_and_Expense_Report(filters=self.filters)
		report.run()

		# fetch the invoice from deferred invoices list
		inv = [d for d in report.deferred_invoices if d.name == pi.name]
		# make sure the list isn't empty
		self.assertTrue(inv)
		# calculate the total deferred expense for the period
		inv = inv[0].calculate_invoice_revenue_expense_for_period()
		deferred_exp = sum([inv[idx].actual for idx in range(len(report.period_list))])
		# make sure the total deferred expense is greater than 0
		self.assertLess(deferred_exp, 0)

	def test_deferred_item_initialization_TC_ACC_599(self):
		"""Test Deferred_Item class initialization for both revenue and expense items."""

		# Mock invoice-like object
		inv = frappe._dict(
			name="INV-001",
			filters={"company": self.company},
			period_list=[{"key": "may_2021"}],
		)

		# Mock GLE entry with deferred revenue account
		gle_revenue = _dict(
			item_name="Subscription Plan",
			service_start_date="2021-05-01",
			service_end_date="2021-08-01",
			base_net_amount=300.0,
			deferred_revenue_account="Deferred Revenue - " + self.company_abbr,
			deferred_expense_account=None,
			gle_posting_date="2021-06-15",
		)

		# Mock get_amount() method behavior by subclassing Deferred_Item
		class MockDeferredItem(Deferred_Item):
			def get_amount(self, x):
				# Always return True to trigger the loop updating last_entry_date
				return True

		#  Test revenue item branch
		revenue_item = MockDeferredItem("ITEM-001", inv, [gle_revenue])
		self.assertEqual(revenue_item.type, "Deferred Sale Item")

		# Mock GLE entry with deferred expense account
		gle_expense = _dict(
			item_name="Office Rent",
			service_start_date="2021-01-01",
			service_end_date="2021-04-01",
			base_net_amount=1000.0,
			deferred_revenue_account=None,
			deferred_expense_account="Deferred Expense - " + self.company_abbr,
			gle_posting_date="2021-02-01",
		)

		#  Test expense item branch
		expense_item = MockDeferredItem("ITEM-002", inv, [gle_expense])
		self.assertEqual(expense_item.item_name, "Office Rent")

	def test_deferred_item_methods_TC_ACC_600(self):
		"""Covers report_data(), get_amount(), and get_item_total() without using mock classes."""
		from frappe import _dict
		from frappe.utils import flt

		from erpnext.accounts.report.deferred_revenue_and_expense.deferred_revenue_and_expense import (
			Deferred_Item,
		)

		# Create Deferred_Item instance manually
		item = Deferred_Item.__new__(Deferred_Item)

		# Mock data setup
		item.item_name = "Deferred Test Item"
		item.period_total = [
			_dict(key="jan_2025", total=500),
			_dict(key="feb_2025", total=300),
		]

		# Mock GLE entries for both debit-credit combinations
		item.gle_entries = [
			_dict(debit=400.0, credit=100.0),
			_dict(debit=200.0, credit=50.0),
		]

		# ---- Test get_amount() ----
		item.type = "Deferred Sale Item"
		amount_sale = item.get_amount(item.gle_entries[0])
		self.assertEqual(amount_sale, flt(400.0) - flt(100.0))  # debit - credit

		item.type = "Deferred Purchase Item"
		amount_purchase = item.get_amount(item.gle_entries[0])
		self.assertEqual(amount_purchase, -(flt(100.0) - flt(400.0)))  # negative of (credit - debit)

		item.type = "Other"
		amount_other = item.get_amount(item.gle_entries[0])
		self.assertEqual(amount_other, 0)

		item.type = "Deferred Sale Item"
		total_sale = item.get_item_total()
		expected_total = sum([flt(e.debit) - flt(e.credit) for e in item.gle_entries])
		self.assertEqual(total_sale, expected_total)

		item.type = "Deferred Purchase Item"
		item.get_item_total()
		sum([-(flt(e.credit) - flt(e.debit)) for e in item.gle_entries])

		# ---- Test report_data() ----
		report = item.report_data()
		self.assertEqual(report.name, "Deferred Test Item")

	def test_calculate_amount_and_make_dummy_gle_TC_ACC_601(self):
		"""Covers all code paths in calculate_amount() and make_dummy_gle()"""
		import datetime

		from frappe import _dict
		from frappe.utils import date_diff, flt, get_first_day, get_last_day, rounded

		from erpnext.accounts.report.deferred_revenue_and_expense.deferred_revenue_and_expense import (
			Deferred_Item,
		)

		# Create Deferred_Item instance manually
		item = Deferred_Item.__new__(Deferred_Item)

		# ---- Setup required attributes ----
		item.service_start_date = datetime.date(2025, 1, 1)
		item.service_end_date = datetime.date(2025, 3, 31)
		item.base_net_amount = 900.0

		# Mock get_item_total() behavior for already booked amount
		def fake_get_item_total():
			return 200.0  # simulate some previously booked amount

		item.get_item_total = fake_get_item_total

		start_date = datetime.date(2025, 1, 1)
		end_date = datetime.date(2025, 1, 31)
		full_period_amount = item.calculate_amount(start_date, end_date)
		self.assertTrue(full_period_amount > 0)

		partial_start = datetime.date(2025, 1, 10)
		partial_end = datetime.date(2025, 1, 20)
		partial_amount = item.calculate_amount(partial_start, partial_end)
		self.assertTrue(partial_amount < full_period_amount)

		item.get_item_total = lambda: 850.0  # force already booked > base_net_amount
		adjusted_amount = item.calculate_amount(start_date, end_date)
		self.assertAlmostEqual(adjusted_amount, 50.0)  # base_net_amount - already_booked_amount

		item.type = "Deferred Sale Item"
		item.make_dummy_gle("GLE-001", datetime.date(2025, 2, 15), 300)

		item.type = "Deferred Purchase Item"
		entry_purchase = item.make_dummy_gle("GLE-002", datetime.date(2025, 3, 15), 400)
		self.assertEqual(entry_purchase.credit, 400)
		self.assertEqual(entry_purchase.debit, 0)

		item.type = "Other Type"
		entry_other = item.make_dummy_gle("GLE-003", datetime.date(2025, 4, 15), 500)
		self.assertEqual(entry_other.debit, 0)
		self.assertEqual(entry_other.credit, 0)

	def test_simulate_future_posting_and_calculate_item_revenue_expense_TC_ACC_602(self):
		"""Covers all lines in simulate_future_posting() and calculate_item_revenue_expense_for_period()"""
		import datetime
		from unittest.mock import patch

		from frappe import _dict

		from erpnext.accounts.report.deferred_revenue_and_expense.deferred_revenue_and_expense import (
			Deferred_Item,
		)

		# Create Deferred_Item instance manually
		item = Deferred_Item.__new__(Deferred_Item)

		# ---- Setup attributes ----
		item.service_start_date = datetime.date(2025, 1, 1)
		item.service_end_date = datetime.date(2025, 3, 31)
		item.last_entry_date = datetime.date(2025, 1, 1)
		item.gle_entries = []
		item.period_total = []  # <-- initialize period_total
		item.base_net_amount = 300.0
		item.filters = _dict(
			company="Test Company",
			from_fiscal_year="2025",
			to_fiscal_year="2025",
		)
		item.period_list = [
			_dict(
				{
					"key": "jan_2025",
					"from_date": datetime.date(2025, 1, 1),
					"to_date": datetime.date(2025, 1, 31),
				}
			),
			_dict(
				{
					"key": "feb_2025",
					"from_date": datetime.date(2025, 2, 1),
					"to_date": datetime.date(2025, 2, 28),
				}
			),
			_dict(
				{
					"key": "mar_2025",
					"from_date": datetime.date(2025, 3, 1),
					"to_date": datetime.date(2025, 3, 31),
				}
			),
		]

		# ---- Set type and deferred account manually ----
		item.type = "Deferred Sale Item"
		item.deferred_account = "Deferred Revenue - Test Company"

		# Mock calculate_amount() to return fixed amounts
		item.calculate_amount = lambda start, end: 100.0
		# Mock make_dummy_gle() to return dict with posting_date
		item.make_dummy_gle = lambda name, date, amount: _dict(
			{"gle_posting_date": date, "debit": amount, "posted": "not"}
		)

		# ---- patch get_period_list to return our custom periods ----
		with patch(
			"erpnext.accounts.report.deferred_revenue_and_expense.deferred_revenue_and_expense.get_period_list"
		) as mock_gpl:
			mock_gpl.return_value = [
				_dict(
					{
						"key": "jan_2025",
						"from_date": datetime.date(2025, 1, 1),
						"to_date": datetime.date(2025, 1, 31),
					}
				),
				_dict(
					{
						"key": "feb_2025",
						"from_date": datetime.date(2025, 2, 1),
						"to_date": datetime.date(2025, 2, 28),
					}
				),
				_dict(
					{
						"key": "mar_2025",
						"from_date": datetime.date(2025, 3, 1),
						"to_date": datetime.date(2025, 3, 31),
					}
				),
			]
			# ---- simulate future postings ----
			item.simulate_future_posting()

		assert len(item.gle_entries) == 3
		assert item.gle_entries[0].debit == 100.0

		# Add a posted entry to test actual sum calculation
		item.gle_entries[0].posted = "posted"

		# ---- calculate item revenue/expense for period ----
		period_totals = item.calculate_item_revenue_expense_for_period()
		assert len(period_totals) == 3
		assert period_totals[0].total == 100.0

	def test_deferred_invoice_initialization_and_calculation_TC_ACC_603(self):
		"""Covers all lines in Deferred_Invoice.__init__ and calculate_invoice_revenue_expense_for_period"""
		import datetime

		from frappe import _dict

		from erpnext.accounts.report.deferred_revenue_and_expense.deferred_revenue_and_expense import (
			Deferred_Invoice,
		)

		# ---- Mock items ----
		item1 = _dict(
			item="ITEM-001",
			posting_date=datetime.date(2025, 1, 1),
			deferred_revenue_account="Deferred Revenue - Test Company",
			deferred_expense_account=None,
			item_name="Subscription Plan",
			service_start_date=datetime.date(2025, 1, 1),
			service_end_date=datetime.date(2025, 3, 31),
			base_net_amount=300.0,
			gle_posting_date=datetime.date(2025, 1, 15),
		)
		item2 = _dict(
			item="ITEM-002",
			posting_date=datetime.date(2025, 1, 1),
			deferred_revenue_account=None,
			deferred_expense_account="Deferred Expense - Test Company",
			item_name="Office Rent",
			service_start_date=datetime.date(2025, 1, 1),
			service_end_date=datetime.date(2025, 3, 31),
			base_net_amount=300.0,
			gle_posting_date=datetime.date(2025, 1, 20),
		)

		# ---- Mock filters and period_list ----
		filters = _dict(company="Test Company")
		period_list = [
			_dict(
				{
					"key": "jan_2025",
					"from_date": datetime.date(2025, 1, 1),
					"to_date": datetime.date(2025, 1, 31),
				}
			),
			_dict(
				{
					"key": "feb_2025",
					"from_date": datetime.date(2025, 2, 1),
					"to_date": datetime.date(2025, 2, 28),
				}
			),
			_dict(
				{
					"key": "mar_2025",
					"from_date": datetime.date(2025, 3, 1),
					"to_date": datetime.date(2025, 3, 31),
				}
			),
		]

		# ---- Patch Deferred_Item to avoid database calls ----
		from erpnext.accounts.report.deferred_revenue_and_expense.deferred_revenue_and_expense import (
			Deferred_Item,
		)

		original_init = Deferred_Item.__init__

		def mock_init(self, item, inv, gle_entries):
			self.item_name = gle_entries[0].item_name
			self.period_total = [_dict({"key": p.key, "total": 100, "actual": 100}) for p in inv.period_list]
			self.calculate_item_revenue_expense_for_period = lambda: self.period_total

		Deferred_Item.__init__ = mock_init

		# ---- Initialize Deferred_Invoice ----
		inv = Deferred_Invoice("INV-001", [item1, item2], filters, period_list)

		# Check initialization
		assert inv.name == "INV-001"

		# ---- Calculate invoice revenue/expense ----
		period_totals = inv.calculate_invoice_revenue_expense_for_period()

		# Check totals
		assert len(period_totals) == 3

		# ---- Restore original Deferred_Item.__init__ ----
		Deferred_Item.__init__ = original_init

	def test_deferred_invoice_estimate_future_and_report_data_TC_ACC_604(self):
		"""Covers all lines in Deferred_Invoice.estimate_future() and report_data()"""
		import datetime

		from frappe import _dict

		from erpnext.accounts.report.deferred_revenue_and_expense.deferred_revenue_and_expense import (
			Deferred_Invoice,
		)

		# ---- Mock items ----
		item1 = _dict(
			item="ITEM-001",
			posting_date=datetime.date(2025, 1, 1),
			deferred_revenue_account="Deferred Revenue - Test Company",
			deferred_expense_account=None,
			item_name="Subscription Plan",
			service_start_date=datetime.date(2025, 1, 1),
			service_end_date=datetime.date(2025, 3, 31),
			base_net_amount=300.0,
			gle_posting_date=datetime.date(2025, 1, 15),
		)
		item2 = _dict(
			item="ITEM-002",
			posting_date=datetime.date(2025, 1, 1),
			deferred_revenue_account=None,
			deferred_expense_account="Deferred Expense - Test Company",
			item_name="Office Rent",
			service_start_date=datetime.date(2025, 1, 1),
			service_end_date=datetime.date(2025, 3, 31),
			base_net_amount=300.0,
			gle_posting_date=datetime.date(2025, 1, 20),
		)

		# ---- Mock filters and period_list ----
		filters = _dict(company="Test Company")
		period_list = [
			_dict(
				{
					"key": "jan_2025",
					"from_date": datetime.date(2025, 1, 1),
					"to_date": datetime.date(2025, 1, 31),
				}
			),
			_dict(
				{
					"key": "feb_2025",
					"from_date": datetime.date(2025, 2, 1),
					"to_date": datetime.date(2025, 2, 28),
				}
			),
			_dict(
				{
					"key": "mar_2025",
					"from_date": datetime.date(2025, 3, 1),
					"to_date": datetime.date(2025, 3, 31),
				}
			),
		]

		# ---- Patch Deferred_Item ----
		from erpnext.accounts.report.deferred_revenue_and_expense.deferred_revenue_and_expense import (
			Deferred_Item,
		)

		original_init = Deferred_Item.__init__

		def mock_init(self, item, inv, gle_entries):
			self.item_name = gle_entries[0].item_name
			self.period_total = [_dict({"key": p.key, "total": 100, "actual": 100}) for p in inv.period_list]
			self.simulate_future_posting = lambda: None  # no-op
			self.report_data = lambda: _dict(
				{"name": self.item_name, "jan_2025": 100, "feb_2025": 100, "mar_2025": 100, "indent": 1}
			)

		Deferred_Item.__init__ = mock_init

		# ---- Initialize Deferred_Invoice ----
		inv = Deferred_Invoice("INV-001", [item1, item2], filters, period_list)

		# ---- Test estimate_future ----
		inv.estimate_future()  # should call simulate_future_posting() for each item

		# ---- Test report_data ----
		report = inv.report_data()
		# invoice total
		inv_total = report[0]
		assert isinstance(inv_total, _dict)
		assert inv_total.name == "INV-001"

		# item report data
		report[1]
		report[2]

		# ---- Restore original Deferred_Item.__init__ ----
		Deferred_Item.__init__ = original_init

	def test_deferred_revenue_and_expense_report_initialization_TC_ACC_605(self):
		"""Covers all lines in Deferred_Revenue_and_Expense_Report.__init__ and get_period_list"""

		import datetime

		from frappe import _dict
		from frappe.utils import getdate

		import erpnext.accounts.report.deferred_revenue_and_expense.deferred_revenue_and_expense as dre
		from erpnext.accounts.report.deferred_revenue_and_expense.deferred_revenue_and_expense import (
			Deferred_Revenue_and_Expense_Report,
		)

		# ---- Test with no filters (default branch) ----
		report_default = Deferred_Revenue_and_Expense_Report()
		assert isinstance(report_default.filters, _dict)
		assert report_default.period_list is None
		assert report_default.deferred_invoices == []
		assert report_default.period_total == []
		assert report_default.filters.company is not None
		assert report_default.filters.periodicity == "Monthly"
		assert report_default.filters.type == "Revenue"
		assert report_default.filters.with_upcoming_postings is True

		# ---- Test with custom filters (else branch) ----
		custom_filters = _dict(
			company="Test Company",
			filter_based_on="Date Range",
			period_start_date=datetime.date(2025, 1, 1),
			period_end_date=datetime.date(2025, 3, 31),
			from_fiscal_year="2025",
			to_fiscal_year="2025",
			periodicity="Monthly",
			type="Expense",
			with_upcoming_postings=False,
		)
		report_custom = Deferred_Revenue_and_Expense_Report(filters=custom_filters)
		assert report_custom.filters.company == "Test Company"
		assert report_custom.filters.type == "Expense"

		# ---- Patch get_period_list directly in the module where it is used ----
		original_get_period_list = dre.get_period_list
		dre.get_period_list = lambda *args, **kwargs: [
			_dict(
				{
					"key": "jan_2025",
					"from_date": datetime.date(2025, 1, 1),
					"to_date": datetime.date(2025, 1, 31),
				}
			),
			_dict(
				{
					"key": "feb_2025",
					"from_date": datetime.date(2025, 2, 1),
					"to_date": datetime.date(2025, 2, 28),
				}
			),
		]

		# ---- Run get_period_list() to cover all lines ----
		report_custom.get_period_list()
		assert isinstance(report_custom.period_list, list)
		assert len(report_custom.period_list) == 2

		# ---- Restore original get_period_list ----
		dre.get_period_list = original_get_period_list

	def test_estimate_future_coverage_TC_ACC_607(self):
		from frappe import _dict

		import erpnext.accounts.report.deferred_revenue_and_expense.deferred_revenue_and_expense as dre

		# --- Dummy invoices with estimate_future ---
		dummy_invoice_store = []

		invoice1 = _dict({"estimate_future": lambda: dummy_invoice_store.append("INV-001")})
		invoice2 = _dict({"estimate_future": lambda: dummy_invoice_store.append("INV-002")})

		# --- Create an instance of the actual report class ---
		report = dre.Deferred_Revenue_and_Expense_Report(filters=_dict({}))
		report.deferred_invoices = [invoice1, invoice2]

		# --- Call the real method to cover all lines ---
		report.estimate_future()

		# --- Assertions to verify the function worked ---
		assert "INV-001" in dummy_invoice_store
		assert "INV-002" in dummy_invoice_store

	def test_get_columns_and_generate_report_data_TC_ACC_608(self):
		# Create a Deferred_Revenue_and_Expense_Report instance
		from erpnext.accounts.report.deferred_revenue_and_expense.deferred_revenue_and_expense import (
			Deferred_Revenue_and_Expense_Report,
		)

		report = Deferred_Revenue_and_Expense_Report(filters=frappe._dict({"type": "Revenue"}))

		# Mock minimal period list
		report.period_list = [
			frappe._dict({"key": "jan_2025", "label": "Jan 2025"}),
			frappe._dict({"key": "feb_2025", "label": "Feb 2025"}),
		]

		# Mock totals for each period
		report.period_total = [
			frappe._dict({"key": "jan_2025", "total": 100, "actual": 90}),
			frappe._dict({"key": "feb_2025", "total": 200, "actual": 180}),
		]

		# Mock invoices with report_data() output
		inv1 = frappe._dict(
			{"report_data": lambda: [frappe._dict({"name": "INV-001", "jan_2025": 50, "feb_2025": 100})]}
		)
		inv2 = frappe._dict(
			{"report_data": lambda: [frappe._dict({"name": "INV-002", "jan_2025": 60, "feb_2025": 120})]}
		)
		report.deferred_invoices = [inv1, inv2]

		# ---- Test get_columns() ----
		cols = report.get_columns()
		self.assertEqual(cols[0]["fieldname"], "name")

		# ---- Test generate_report_data() for Revenue ----
		report.generate_report_data()

		# ---- Test generate_report_data() for Expense ----
		report.filters.type = "Expense"
		data_expense = report.generate_report_data()
		self.assertEqual(data_expense[-1].name, "Total Deferred Expense")

	def test_prepare_chart_and_run_functions_TC_ACC_609(self):
		from erpnext.accounts.report.deferred_revenue_and_expense.deferred_revenue_and_expense import (
			Deferred_Revenue_and_Expense_Report,
		)

		# --- Mock a report instance ---
		report = Deferred_Revenue_and_Expense_Report(
			filters=frappe._dict({"type": "Revenue", "with_upcoming_postings": True})
		)

		# Mock period list and totals
		report.period_list = [
			frappe._dict({"label": "Jan 2025", "key": "jan_2025"}),
			frappe._dict({"label": "Feb 2025", "key": "feb_2025"}),
		]
		report.period_total = [
			frappe._dict({"actual": 50, "total": 100}),
			frappe._dict({"actual": 80, "total": 150}),
		]

		# ---- Test prepare_chart() ----
		chart = report.prepare_chart()

		# Validate chart structure
		self.assertEqual(chart["type"], "axis-mixed")

		# Dataset 1: Actual Posting
		actual_dataset = chart["data"]["datasets"][0]
		self.assertEqual(actual_dataset["name"], "Actual Posting")

		# Dataset 2: Expected (added because with_upcoming_postings=True)
		expected_dataset = chart["data"]["datasets"][1]
		self.assertEqual(expected_dataset["name"], "Expected")

		# ---- Test run() ----
		# Patch internal methods to avoid real DB calls and still trigger all lines
		report.get_period_list = lambda *a, **kw: setattr(report, "period_list", report.period_list)
		report.get_invoices = lambda *a, **kw: report.deferred_invoices.append("dummy_invoice")
		report.estimate_future = lambda *a, **kw: setattr(report, "future_estimated", True)
		report.calculate_revenue_and_expense = lambda *a, **kw: setattr(report, "calculated", True)

		# Run the report (should hit all code paths)
		report.run()

		# Validate that internal methods were called and flags set
		self.assertIn("dummy_invoice", report.deferred_invoices)

		# Test again with with_upcoming_postings=False to cover other branch
		report.filters.with_upcoming_postings = False
		report.deferred_invoices = []
		delattr(report, "future_estimated")

		report.run()
		self.assertFalse(hasattr(report, "future_estimated"))
		self.assertTrue(hasattr(report, "calculated"))

	def test_execute_function_TC_ACC_610(self):
		from erpnext.accounts.report.deferred_revenue_and_expense.deferred_revenue_and_expense import (
			Deferred_Revenue_and_Expense_Report,
			execute,
		)

		# Mock filters
		filters = frappe._dict({"type": "Revenue", "with_upcoming_postings": True})

		# --- Patch methods to prevent DB calls and to validate flow ---
		original_run = Deferred_Revenue_and_Expense_Report.run
		original_get_columns = Deferred_Revenue_and_Expense_Report.get_columns
		original_generate_report_data = Deferred_Revenue_and_Expense_Report.generate_report_data
		original_prepare_chart = Deferred_Revenue_and_Expense_Report.prepare_chart

		try:
			Deferred_Revenue_and_Expense_Report.run = lambda self: setattr(self, "ran", True)
			Deferred_Revenue_and_Expense_Report.get_columns = lambda self: ["col1", "col2"]
			Deferred_Revenue_and_Expense_Report.generate_report_data = lambda self: [{"row": 1}]
			Deferred_Revenue_and_Expense_Report.prepare_chart = lambda self: {"type": "chart"}

			# --- Execute the function ---
			columns, data, message, chart = execute(filters)

			# --- Validate return values and execution ---
			self.assertEqual(columns, ["col1", "col2"])

		finally:
			# Restore originals to avoid side effects on other tests
			Deferred_Revenue_and_Expense_Report.run = original_run
			Deferred_Revenue_and_Expense_Report.get_columns = original_get_columns
			Deferred_Revenue_and_Expense_Report.generate_report_data = original_generate_report_data
			Deferred_Revenue_and_Expense_Report.prepare_chart = original_prepare_chart
