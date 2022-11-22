import frappe
from frappe import qb
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, flt, nowdate

from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note
from erpnext.accounts.doctype.sales_invoice.test_sales_invoice import create_sales_invoice
from erpnext.accounts.report.gross_profit.gross_profit import execute
from erpnext.stock.doctype.item.test_item import create_item
from erpnext.stock.doctype.stock_entry.stock_entry_utils import make_stock_entry


class TestGrossProfit(FrappeTestCase):
	def setUp(self):
		self.create_company()
		self.create_item()
		self.create_customer()
		self.create_sales_invoice()
		self.clear_old_entries()

	def tearDown(self):
		frappe.db.rollback()

	def create_company(self):
		company_name = "_Test Gross Profit"
		abbr = "_GP"
		if frappe.db.exists("Company", company_name):
			company = frappe.get_doc("Company", company_name)
		else:
			company = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": company_name,
					"country": "India",
					"default_currency": "INR",
					"create_chart_of_accounts_based_on": "Standard Template",
					"chart_of_accounts": "Standard",
				}
			)
			company = company.save()

		self.company = company.name
		self.cost_center = company.cost_center
		self.warehouse = "Stores - " + abbr
		self.income_account = "Sales - " + abbr
		self.expense_account = "Cost of Goods Sold - " + abbr
		self.debit_to = "Debtors - " + abbr
		self.creditors = "Creditors - " + abbr

	def create_item(self):
		item = create_item(
			item_code="_Test GP Item", is_stock_item=1, company=self.company, warehouse=self.warehouse
		)
		self.item = item if isinstance(item, str) else item.item_code

	def create_customer(self):
		name = "_Test GP Customer"
		if frappe.db.exists("Customer", name):
			self.customer = name
		else:
			customer = frappe.new_doc("Customer")
			customer.customer_name = name
			customer.type = "Individual"
			customer.save()
			self.customer = customer.name

	def create_sales_invoice(
		self, qty=1, rate=100, posting_date=nowdate(), do_not_save=False, do_not_submit=False
	):
		"""
		Helper function to populate default values in sales invoice
		"""
		sinv = create_sales_invoice(
			qty=qty,
			rate=rate,
			company=self.company,
			customer=self.customer,
			item_code=self.item,
			item_name=self.item,
			cost_center=self.cost_center,
			warehouse=self.warehouse,
			debit_to=self.debit_to,
			parent_cost_center=self.cost_center,
			update_stock=0,
			currency="INR",
			is_pos=0,
			is_return=0,
			return_against=None,
			income_account=self.income_account,
			expense_account=self.expense_account,
			do_not_save=do_not_save,
			do_not_submit=do_not_submit,
		)
		return sinv

	def clear_old_entries(self):
		doctype_list = [
			"Sales Invoice",
			"GL Entry",
			"Stock Entry",
			"Stock Ledger Entry",
			"Delivery Note",
		]
		for doctype in doctype_list:
			qb.from_(qb.DocType(doctype)).delete().where(qb.DocType(doctype).company == self.company).run()

	def test_invoice_without_only_delivery_note(self):
		"""
		Test buying amount for Invoice without `update_stock` flag set but has Delivery Note
		"""
		se = make_stock_entry(
			company=self.company,
			item_code=self.item,
			target=self.warehouse,
			qty=1,
			basic_rate=100,
			do_not_submit=True,
		)
		item = se.items[0]
		se.append(
			"items",
			{
				"item_code": item.item_code,
				"s_warehouse": item.s_warehouse,
				"t_warehouse": item.t_warehouse,
				"qty": 1,
				"basic_rate": 200,
				"conversion_factor": item.conversion_factor or 1.0,
				"transfer_qty": flt(item.qty) * (flt(item.conversion_factor) or 1.0),
				"serial_no": item.serial_no,
				"batch_no": item.batch_no,
				"cost_center": item.cost_center,
				"expense_account": item.expense_account,
			},
		)
		se = se.save().submit()

		sinv = create_sales_invoice(
			qty=1,
			rate=100,
			company=self.company,
			customer=self.customer,
			item_code=self.item,
			item_name=self.item,
			cost_center=self.cost_center,
			warehouse=self.warehouse,
			debit_to=self.debit_to,
			parent_cost_center=self.cost_center,
			update_stock=0,
			currency="INR",
			income_account=self.income_account,
			expense_account=self.expense_account,
		)

		filters = frappe._dict(
			company=self.company, from_date=nowdate(), to_date=nowdate(), group_by="Invoice"
		)

		columns, data = execute(filters=filters)

		# Without Delivery Note, buying rate should be 150
		expected_entry_without_dn = {
			"parent_invoice": sinv.name,
			"currency": "INR",
			"sales_invoice": self.item,
			"customer": self.customer,
			"posting_date": frappe.utils.datetime.date.fromisoformat(nowdate()),
			"item_code": self.item,
			"item_name": self.item,
			"warehouse": "Stores - _GP",
			"qty": 1.0,
			"avg._selling_rate": 100.0,
			"valuation_rate": 150.0,
			"selling_amount": 100.0,
			"buying_amount": 150.0,
			"gross_profit": -50.0,
			"gross_profit_%": -50.0,
		}
		gp_entry = [x for x in data if x.parent_invoice == sinv.name]
		self.assertDictContainsSubset(expected_entry_without_dn, gp_entry[0])

		# make delivery note
		dn = make_delivery_note(sinv.name)
		dn.items[0].qty = 1
		dn = dn.save().submit()

		columns, data = execute(filters=filters)

		# Without Delivery Note, buying rate should be 100
		expected_entry_with_dn = {
			"parent_invoice": sinv.name,
			"currency": "INR",
			"sales_invoice": self.item,
			"customer": self.customer,
			"posting_date": frappe.utils.datetime.date.fromisoformat(nowdate()),
			"item_code": self.item,
			"item_name": self.item,
			"warehouse": "Stores - _GP",
			"qty": 1.0,
			"avg._selling_rate": 100.0,
			"valuation_rate": 100.0,
			"selling_amount": 100.0,
			"buying_amount": 100.0,
			"gross_profit": 0.0,
			"gross_profit_%": 0.0,
		}
		gp_entry = [x for x in data if x.parent_invoice == sinv.name]
		self.assertDictContainsSubset(expected_entry_with_dn, gp_entry[0])
