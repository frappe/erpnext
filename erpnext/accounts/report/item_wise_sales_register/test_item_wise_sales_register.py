import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, today

from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.item_wise_sales_register.item_wise_sales_register import execute
from erpnext.accounts.test.accounts_mixin import AccountsTestMixin


class TestItemWiseSalesRegister(AccountsTestMixin, FrappeTestCase):
	def setUp(self):
		self.create_company()
		self.create_customer()
		self.create_item()
		self.clear_old_entries()

	def tearDown(self):
		frappe.db.rollback()

	def create_sales_invoice(self, item=None, taxes=None, do_not_submit=False):
		si = create_sales_invoice(
			item=item or self.item,
			item_name=item or self.item,
			description=item or self.item,
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

		for tax in taxes or []:
			si.append(
				"taxes",
				{
					"charge_type": "On Net Total",
					"account_head": tax["account_head"],
					"cost_center": self.cost_center,
					"description": tax["description"],
					"rate": tax["rate"],
				},
			)

		si = si.save()
		if not do_not_submit:
			si = si.submit()
		return si

	def test_basic_report_output(self):
		si = self.create_sales_invoice()

		filters = frappe._dict({"from_date": today(), "to_date": today(), "company": self.company})
		report = execute(filters)

		self.assertEqual(len(report[1]), 1)

		expected_result = {
			"item_code": si.items[0].item_code,
			"invoice": si.name,
			"posting_date": getdate(),
			"customer": si.customer,
			"debit_to": si.debit_to,
			"company": self.company,
			"income_account": si.items[0].income_account,
			"stock_qty": 1.0,
			"stock_uom": si.items[0].stock_uom,
			"rate": 100.0,
			"amount": 100.0,
			"total_tax": 0,
			"total_other_charges": 0,
			"total": 100.0,
			"currency": "INR",
		}

		report_output = {k: v for k, v in report[1][0].items() if k in expected_result}
		self.assertDictEqual(report_output, expected_result)

	def test_tax_columns_are_split_by_account(self):
		self.create_sales_invoice(
			taxes=[
				{"account_head": "_Test Account VAT - _TC", "description": "GST", "rate": 5},
				{"account_head": "_Test Account Service Tax - _TC", "description": "GST", "rate": 2},
			]
		)

		filters = frappe._dict({"from_date": today(), "to_date": today(), "company": self.company})
		row = execute(filters)[1][0]

		vat, service_tax = (frappe.scrub(f"_Test Account {name} - _TC") for name in ("VAT", "Service Tax"))
		self.assertEqual((row[f"{vat}_rate"], row[f"{vat}_amount"]), (5, 5))
		self.assertEqual((row[f"{service_tax}_rate"], row[f"{service_tax}_amount"]), (2, 2))

	def test_tax_rows_on_same_account_combine_rates(self):
		self.create_sales_invoice(
			taxes=[
				{"account_head": "_Test Account VAT - _TC", "description": "VAT A", "rate": 2},
				{"account_head": "_Test Account VAT - _TC", "description": "VAT B", "rate": 2},
			]
		)

		filters = frappe._dict({"from_date": today(), "to_date": today(), "company": self.company})
		row = execute(filters)[1][0]

		vat = frappe.scrub("_Test Account VAT - _TC")
		self.assertEqual((row[f"{vat}_rate"], row[f"{vat}_amount"]), (4, 4))

	def test_accounts_with_same_scrubbed_name_keep_their_own_columns(self):
		accounts = [self.create_tax_account(name) for name in ("_Test Tax-1", "_Test Tax 1")]
		customers = ("_Test Customer", "_Test Customer 1")
		for customer, account in zip(customers, accounts, strict=True):
			self.customer = customer
			self.create_sales_invoice(taxes=[{"account_head": account, "description": "Tax", "rate": 5}])

		all_fieldnames = self.get_amount_fieldnames()
		self.assertEqual(len(set(all_fieldnames.values())), 2)
		for customer, account in zip(customers, accounts, strict=True):
			# filtering out the other account must not move this account to another column
			fieldnames = self.get_amount_fieldnames(customer=customer)
			self.assertEqual(fieldnames, {account: all_fieldnames[account]})

	def get_amount_fieldnames(self, **filters):
		filters = frappe._dict(from_date=today(), to_date=today(), company=self.company, **filters)
		columns = execute(filters)[0]
		return {
			column["label"].removesuffix(" Amount"): column["fieldname"]
			for column in columns
			if column["fieldname"].endswith("_amount") and column["label"].startswith("_Test Tax")
		}

	def create_tax_account(self, account_name):
		account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": account_name,
				"parent_account": "Duties and Taxes - _TC",
				"company": self.company,
				"account_type": "Tax",
			}
		).insert()
		return account.name

	def test_grouped_report_handles_different_tax_descriptions(self):
		self.create_item(item_name="_Test Item Tax Description A")
		first_item = self.item
		self.create_item(item_name="_Test Item Tax Description B")
		second_item = self.item

		first_tax_description = "Tax Description A"
		second_tax_description = "Tax Description B"
		first_tax_amount_field = f"{frappe.scrub('_Test Account VAT - _TC')}_amount"
		second_tax_amount_field = f"{frappe.scrub('_Test Account Service Tax - _TC')}_amount"

		self.create_sales_invoice(
			item=first_item,
			taxes=[
				{
					"account_head": "_Test Account VAT - _TC",
					"description": first_tax_description,
					"rate": 5,
				}
			],
		)
		self.create_sales_invoice(
			item=second_item,
			taxes=[
				{
					"account_head": "_Test Account Service Tax - _TC",
					"description": second_tax_description,
					"rate": 2,
				}
			],
		)

		filters = frappe._dict(
			{
				"from_date": today(),
				"to_date": today(),
				"company": self.company,
				"group_by": "Customer",
			}
		)
		_, data, _, _, _, _ = execute(filters)

		grand_total_row = next(row for row in data if row.get("bold") and row.get("item_code") == "Total")

		self.assertEqual(grand_total_row[first_tax_amount_field], 5.0)
		self.assertEqual(grand_total_row[second_tax_amount_field], 2.0)
