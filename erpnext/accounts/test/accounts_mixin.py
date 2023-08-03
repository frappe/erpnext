import frappe

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
		self.debit_usd = "Debtors USD - " + abbr
		self.cash = "Cash - " + abbr
		self.creditors = "Creditors - " + abbr

		# create bank account
		bank_account = "HDFC - " + abbr
		if frappe.db.exists("Account", bank_account):
			self.bank = bank_account
		else:
			bank_acc = frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "HDFC",
					"parent_account": "Bank Accounts - " + abbr,
					"company": self.company,
				}
			)
			bank_acc.save()
			self.bank = bank_acc.name
