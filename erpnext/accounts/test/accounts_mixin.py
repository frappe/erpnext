import frappe
from frappe import qb

from erpnext.stock.doctype.item.test_item import create_item


class AccountsTestMixin:
	def create_customer(self, customer_name="_Test Customer", currency=None):
		if not frappe.db.exists("Customer", customer_name):
			customer = frappe.new_doc("Customer")
			customer.customer_name = customer_name
			customer.type = "Individual"

			if currency:
				customer.default_currency = currency
			customer.save()
			self.customer = customer.name
		else:
			self.customer = customer_name

	def create_supplier(self, supplier_name="_Test Supplier", currency=None):
		if not frappe.db.exists("Supplier", supplier_name):
			supplier = frappe.new_doc("Supplier")
			supplier.supplier_name = supplier_name
			supplier.supplier_type = "Individual"
			supplier.supplier_group = "Local"

			if currency:
				supplier.default_currency = currency
			supplier.save()
			self.supplier = supplier.name
		else:
			self.supplier = supplier_name

	def create_item(self, item_name="_Test Item", is_stock=0, warehouse=None, company=None):
		item = create_item(item_name, is_stock_item=is_stock, warehouse=warehouse, company=company)
		self.item = item.name

	def create_company(self, company_name="_Test Company", abbr="_TC"):
		self.company_abbr = abbr
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
		self.finished_warehouse = "Finished Goods - " + abbr
		self.income_account = "Sales - " + abbr
		self.expense_account = "Cost of Goods Sold - " + abbr
		self.debit_to = "Debtors - " + abbr
		self.cash = "Cash - " + abbr
		self.creditors = "Creditors - " + abbr
		self.retained_earnings = "Retained Earnings - " + abbr

		# Deferred revenue, expense and bank accounts
		other_accounts = [
			frappe._dict(
				{
					"attribute_name": "deferred_revenue",
					"account_name": "Deferred Revenue",
					"parent_account": "Current Liabilities - " + abbr,
				}
			),
			frappe._dict(
				{
					"attribute_name": "deferred_expense",
					"account_name": "Deferred Expense",
					"parent_account": "Current Assets - " + abbr,
				}
			),
			frappe._dict(
				{
					"attribute_name": "bank",
					"account_name": "HDFC",
					"parent_account": "Bank Accounts - " + abbr,
				}
			),
			frappe._dict(
				{
					"attribute_name": "advance_received",
					"account_name": "Advance Received",
					"parent_account": "Current Liabilities - " + abbr,
					"account_type": "Receivable",
				}
			),
			frappe._dict(
				{
					"attribute_name": "advance_paid",
					"account_name": "Advance Paid",
					"parent_account": "Current Assets - " + abbr,
					"account_type": "Payable",
				}
			),
		]
		for acc in other_accounts:
			acc_name = acc.account_name + " - " + abbr
			if frappe.db.exists("Account", acc_name):
				setattr(self, acc.attribute_name, acc_name)
			else:
				new_acc = frappe.get_doc(
					{
						"doctype": "Account",
						"account_name": acc.account_name,
						"parent_account": acc.parent_account,
						"company": self.company,
					}
				)
				new_acc.account_type = acc.get("account_type", None)
				new_acc.save()
				setattr(self, acc.attribute_name, new_acc.name)

		self.identify_default_warehouses()

	def enable_advance_as_liability(self):
		company = frappe.get_doc("Company", self.company)
		company.book_advance_payments_in_separate_party_account = True
		company.default_advance_received_account = self.advance_received
		company.default_advance_paid_account = self.advance_paid
		company.save()

	def disable_advance_as_liability(self):
		company = frappe.get_doc("Company", self.company)
		company.book_advance_payments_in_separate_party_account = False
		company.default_advance_paid_account = company.default_advance_received_account = None
		company.save()

	def identify_default_warehouses(self):
		for w in frappe.db.get_all(
			"Warehouse", filters={"company": self.company}, fields=["name", "warehouse_name"]
		):
			setattr(self, "warehouse_" + w.warehouse_name.lower().strip().replace(" ", "_"), w.name)

	def create_usd_receivable_account(self):
		account_name = "Debtors USD"
		if not frappe.db.get_value(
			"Account", filters={"account_name": account_name, "company": self.company}
		):
			acc = frappe.new_doc("Account")
			acc.account_name = account_name
			acc.parent_account = "Accounts Receivable - " + self.company_abbr
			acc.company = self.company
			acc.account_currency = "USD"
			acc.account_type = "Receivable"
			acc.insert()
		else:
			name = frappe.db.get_value(
				"Account",
				filters={"account_name": account_name, "company": self.company},
				fieldname="name",
				pluck=True,
			)
			acc = frappe.get_doc("Account", name)
		self.debtors_usd = acc.name

	def create_usd_payable_account(self):
		account_name = "Creditors USD"
		if not frappe.db.get_value(
			"Account", filters={"account_name": account_name, "company": self.company}
		):
			acc = frappe.new_doc("Account")
			acc.account_name = account_name
			acc.parent_account = "Accounts Payable - " + self.company_abbr
			acc.company = self.company
			acc.account_currency = "USD"
			acc.account_type = "Payable"
			acc.insert()
		else:
			name = frappe.db.get_value(
				"Account",
				filters={"account_name": account_name, "company": self.company},
				fieldname="name",
				pluck=True,
			)
			acc = frappe.get_doc("Account", name)
		self.creditors_usd = acc.name

	def clear_old_entries(self):
		doctype_list = [
			"GL Entry",
			"Payment Ledger Entry",
			"Sales Invoice",
			"Purchase Invoice",
			"Payment Entry",
			"Journal Entry",
			"Sales Order",
			"Exchange Rate Revaluation",
			"Bank Account",
			"Bank Transaction",
		]
		for doctype in doctype_list:
			qb.from_(qb.DocType(doctype)).delete().where(qb.DocType(doctype).company == self.company).run()
