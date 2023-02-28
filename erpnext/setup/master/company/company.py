# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
import frappe.defaults
from frappe import _
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.query_builder import Field
from frappe.utils import cint, formatdate, get_timestamp, today
from frappe.utils.nestedset import NestedSet
from master.master.doctype.company.company import Company

from erpnext.accounts.doctype.account.account import get_account_currency
from erpnext.setup.setup_wizard.operations.taxes_setup import setup_taxes_and_charges


class ERPNextCompany(Company):
	@frappe.whitelist()
	def check_if_transactions_exist(self):
		exists = False
		for doctype in [
			"Sales Invoice",
			"Delivery Note",
			"Sales Order",
			"Quotation",
			"Purchase Invoice",
			"Purchase Receipt",
			"Purchase Order",
			"Supplier Quotation",
		]:
			if (
				frappe.qb.from_(doctype)
				.select("name")
				.where((Field("company") == self.name) & (Field("docstatus") == 1))
				.limit(1)
			).run():
				exists = True
				break

		return exists

	def validate(self):
		self.update_default_account = False
		if self.is_new():
			self.update_default_account = True

		self.validate_default_accounts()
		self.validate_currency()
		self.validate_coa_input()
		self.validate_perpetual_inventory()
		self.validate_provisional_account_for_non_stock_items()

		super(ERPNextCompany, self).validate()

	@frappe.whitelist()
	def create_default_tax_template(self):
		setup_taxes_and_charges(self.name, self.country)

	def validate_default_accounts(self):
		accounts = [
			["Default Bank Account", "default_bank_account"],
			["Default Cash Account", "default_cash_account"],
			["Default Receivable Account", "default_receivable_account"],
			["Default Payable Account", "default_payable_account"],
			["Default Expense Account", "default_expense_account"],
			["Default Income Account", "default_income_account"],
			["Stock Received But Not Billed Account", "stock_received_but_not_billed"],
			["Stock Adjustment Account", "stock_adjustment_account"],
			["Expense Included In Valuation Account", "expenses_included_in_valuation"],
		]

		for account in accounts:
			if self.get(account[1]):
				for_company = frappe.db.get_value("Account", self.get(account[1]), "company")
				if for_company != self.name:
					frappe.throw(
						_("Account {0} does not belong to company: {1}").format(self.get(account[1]), self.name)
					)

				if get_account_currency(self.get(account[1])) != self.default_currency:
					error_message = _(
						"{0} currency must be same as company's default currency. Please select another account."
					).format(frappe.bold(account[0]))
					frappe.throw(error_message)

	def validate_currency(self):
		if self.is_new():
			return

		self.previous_default_currency = frappe.get_cached_value(
			"Company", self.name, "default_currency"
		)

		if (
			self.default_currency
			and self.previous_default_currency
			and self.default_currency != self.previous_default_currency
			and self.check_if_transactions_exist()
		):
			frappe.throw(
				_(
					"Cannot change company's default currency, because there are existing transactions. Transactions must be cancelled to change the default currency."
				)
			)

	def on_update(self):
		NestedSet.on_update(self)

		if not (
			frappe.qb.from_("Account")
			.select("name")
			.where((Field("company") == self.name) & (Field("docstatus") < 2))
		).run():
			if not frappe.local.flags.ignore_chart_of_accounts:
				frappe.flags.country_change = True
				self.create_default_accounts()
				self.create_default_warehouses()

		if not frappe.db.get_value("Cost Center", {"is_group": 0, "company": self.name}):
			self.create_default_cost_center()

		if frappe.flags.country_change:
			install_country_fixtures(self.name, self.country)
			self.create_default_tax_template()

		if not frappe.db.get_value("Department", {"company": self.name}):
			self.create_default_departments()

		if not frappe.local.flags.ignore_chart_of_accounts:
			self.set_default_accounts()
			if self.default_cash_account:
				self.set_mode_of_payment_account()

		if (
			hasattr(frappe.local, "enable_perpetual_inventory")
			and self.name in frappe.local.enable_perpetual_inventory
		):
			frappe.local.enable_perpetual_inventory[self.name] = self.enable_perpetual_inventory

		super(ERPNextCompany, self).on_update()

	def create_default_accounts(self):
		from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import create_charts

		frappe.local.flags.ignore_root_company_validation = True
		create_charts(self.name, self.chart_of_accounts, self.existing_company)

		self.db_set(
			"default_receivable_account",
			frappe.db.get_value(
				"Account", {"company": self.name, "account_type": "Receivable", "is_group": 0}
			),
		)

		self.db_set(
			"default_payable_account",
			frappe.db.get_value(
				"Account", {"company": self.name, "account_type": "Payable", "is_group": 0}
			),
		)

	def validate_coa_input(self):
		if self.create_chart_of_accounts_based_on == "Existing Company":
			self.chart_of_accounts = None
			if not self.existing_company:
				frappe.throw(_("Please select Existing Company for creating Chart of Accounts"))

		else:
			self.existing_company = None
			self.create_chart_of_accounts_based_on = "Standard Template"
			if not self.chart_of_accounts:
				self.chart_of_accounts = "Standard"

	def validate_perpetual_inventory(self):
		if not self.get("__islocal"):
			if cint(self.enable_perpetual_inventory) == 1 and not self.default_inventory_account:
				frappe.msgprint(
					_("Set default inventory account for perpetual inventory"), alert=True, indicator="orange"
				)

	def validate_provisional_account_for_non_stock_items(self):
		if not self.get("__islocal"):
			if (
				cint(self.enable_provisional_accounting_for_non_stock_items) == 1
				and not self.default_provisional_account
			):
				frappe.throw(
					_("Set default {0} account for non stock items").format(frappe.bold("Provisional Account"))
				)

			make_property_setter(
				"Purchase Receipt",
				"provisional_expense_account",
				"hidden",
				not self.enable_provisional_accounting_for_non_stock_items,
				"Check",
				validate_fields_for_doctype=False,
			)

	def set_default_accounts(self):
		default_accounts = {
			"default_cash_account": "Cash",
			"default_bank_account": "Bank",
			"round_off_account": "Round Off",
			"accumulated_depreciation_account": "Accumulated Depreciation",
			"depreciation_expense_account": "Depreciation",
			"capital_work_in_progress_account": "Capital Work in Progress",
			"asset_received_but_not_billed": "Asset Received But Not Billed",
			"expenses_included_in_asset_valuation": "Expenses Included In Asset Valuation",
			"default_expense_account": "Cost of Goods Sold",
		}

		if self.enable_perpetual_inventory:
			default_accounts.update(
				{
					"stock_received_but_not_billed": "Stock Received But Not Billed",
					"default_inventory_account": "Stock",
					"stock_adjustment_account": "Stock Adjustment",
					"expenses_included_in_valuation": "Expenses Included In Valuation",
				}
			)

		if self.update_default_account:
			for default_account in default_accounts:
				self._set_default_account(default_account, default_accounts.get(default_account))

		if not self.default_income_account:
			income_account = frappe.db.get_value(
				"Account", {"account_name": _("Sales"), "company": self.name, "is_group": 0}
			)

			if not income_account:
				income_account = frappe.db.get_value(
					"Account", {"account_name": _("Sales Account"), "company": self.name}
				)

			self.db_set("default_income_account", income_account)

		if not self.default_payable_account:
			self.db_set("default_payable_account", self.default_payable_account)

		if not self.write_off_account:
			write_off_acct = frappe.db.get_value(
				"Account", {"account_name": _("Write Off"), "company": self.name, "is_group": 0}
			)

			self.db_set("write_off_account", write_off_acct)

		if not self.exchange_gain_loss_account:
			exchange_gain_loss_acct = frappe.db.get_value(
				"Account", {"account_name": _("Exchange Gain/Loss"), "company": self.name, "is_group": 0}
			)

			self.db_set("exchange_gain_loss_account", exchange_gain_loss_acct)

		if not self.disposal_account:
			disposal_acct = frappe.db.get_value(
				"Account",
				{"account_name": _("Gain/Loss on Asset Disposal"), "company": self.name, "is_group": 0},
			)

			self.db_set("disposal_account", disposal_acct)

	def _set_default_account(self, fieldname, account_type):
		if self.get(fieldname):
			return

		account = frappe.db.get_value(
			"Account", {"account_type": account_type, "is_group": 0, "company": self.name}
		)

		if account:
			self.db_set(fieldname, account)

	def set_mode_of_payment_account(self):
		cash = frappe.db.get_value("Mode of Payment", {"type": "Cash"}, "name")
		if (
			cash
			and self.default_cash_account
			and not frappe.db.get_value("Mode of Payment Account", {"company": self.name, "parent": cash})
		):
			mode_of_payment = frappe.get_doc("Mode of Payment", cash, for_update=True)
			mode_of_payment.append(
				"accounts", {"company": self.name, "default_account": self.default_cash_account}
			)
			mode_of_payment.save(ignore_permissions=True)

	def create_default_cost_center(self):
		cc_list = [
			{
				"cost_center_name": self.name,
				"company": self.name,
				"is_group": 1,
				"parent_cost_center": None,
			},
			{
				"cost_center_name": _("Main"),
				"company": self.name,
				"is_group": 0,
				"parent_cost_center": self.name + " - " + self.abbr,
			},
		]
		for cc in cc_list:
			cc.update({"doctype": "Cost Center"})
			cc_doc = frappe.get_doc(cc)
			cc_doc.flags.ignore_permissions = True

			if cc.get("cost_center_name") == self.name:
				cc_doc.flags.ignore_mandatory = True
			cc_doc.insert()

		self.db_set("cost_center", _("Main") + " - " + self.abbr)
		self.db_set("round_off_cost_center", _("Main") + " - " + self.abbr)
		self.db_set("depreciation_cost_center", _("Main") + " - " + self.abbr)

	def on_trash(self):
		"""
		Trash accounts and cost centers for this company if no gl entry exists
		"""
		NestedSet.validate_if_child_exists(self)
		frappe.utils.nestedset.update_nsm(self)

		rec = frappe.db.sql("SELECT name from `tabGL Entry` where company = %s", self.name)
		if not rec:
			frappe.db.sql(
				"""delete from `tabBudget Account`
				where exists(select name from tabBudget
					where name=`tabBudget Account`.parent and company = %s)""",
				self.name,
			)

			for doctype in ["Account", "Cost Center", "Budget", "Party Account"]:
				frappe.db.sql("delete from `tab{0}` where company = %s".format(doctype), self.name)

		if not frappe.db.get_value("Stock Ledger Entry", {"company": self.name}):
			frappe.db.sql("""delete from `tabWarehouse` where company=%s""", self.name)

		frappe.defaults.clear_default("company", value=self.name)
		for doctype in ["Mode of Payment Account", "Item Default"]:
			frappe.db.sql("delete from `tab{0}` where company = %s".format(doctype), self.name)

		# clear default accounts, warehouses from item
		warehouses = frappe.db.sql_list("select name from tabWarehouse where company=%s", self.name)
		if warehouses:
			frappe.db.sql(
				"""delete from `tabItem Reorder` where warehouse in (%s)"""
				% ", ".join(["%s"] * len(warehouses)),
				tuple(warehouses),
			)

		# reset default company
		frappe.db.sql(
			"""update `tabSingles` set value=''
			where doctype='Global Defaults' and field='default_company'
			and value=%s""",
			self.name,
		)

		# reset default company
		frappe.db.sql(
			"""update `tabSingles` set value=''
			where doctype='Chart of Accounts Importer' and field='company'
			and value=%s""",
			self.name,
		)

		# delete BOMs
		boms = frappe.db.sql_list("select name from tabBOM where company=%s", self.name)
		if boms:
			frappe.db.sql("delete from tabBOM where company=%s", self.name)
			for dt in ("BOM Operation", "BOM Item", "BOM Scrap Item", "BOM Explosion Item"):
				frappe.db.sql(
					"delete from `tab%s` where parent in (%s)" "" % (dt, ", ".join(["%s"] * len(boms))),
					tuple(boms),
				)

		frappe.db.sql("delete from tabEmployee where company=%s", self.name)
		frappe.db.sql("delete from tabDepartment where company=%s", self.name)
		frappe.db.sql("delete from `tabTax Withholding Account` where company=%s", self.name)
		frappe.db.sql("delete from `tabTransaction Deletion Record` where company=%s", self.name)

		# delete tax templates
		frappe.db.sql("delete from `tabSales Taxes and Charges Template` where company=%s", self.name)
		frappe.db.sql("delete from `tabPurchase Taxes and Charges Template` where company=%s", self.name)
		frappe.db.sql("delete from `tabItem Tax Template` where company=%s", self.name)

		# delete Process Deferred Accounts if no GL Entry found
		if not frappe.db.get_value("GL Entry", {"company": self.name}):
			frappe.db.sql("delete from `tabProcess Deferred Accounting` where company=%s", self.name)


def install_country_fixtures(company, country):
	try:
		module_name = f"erpnext.regional.{frappe.scrub(country)}.setup.setup"
		frappe.get_attr(module_name)(company, False)
	except ImportError:
		pass
	except Exception:
		frappe.log_error("Unable to set country fixtures")
		frappe.throw(
			_("Failed to setup defaults for country {0}. Please contact support.").format(
				frappe.bold(country)
			)
		)


def update_company_current_month_sales(company):
	current_month_year = formatdate(today(), "MM-yyyy")

	results = frappe.db.sql(
		"""
		SELECT
			SUM(base_grand_total) AS total,
			DATE_FORMAT(`posting_date`, '%m-%Y') AS month_year
		FROM
			`tabSales Invoice`
		WHERE
			DATE_FORMAT(`posting_date`, '%m-%Y') = '{current_month_year}'
			AND docstatus = 1
			AND company = {company}
		GROUP BY
			month_year
	""".format(
			current_month_year=current_month_year, company=frappe.db.escape(company)
		),
		as_dict=True,
	)

	monthly_total = results[0]["total"] if len(results) > 0 else 0

	frappe.db.set_value("Company", company, "total_monthly_sales", monthly_total)


def update_company_monthly_sales(company):
	"""Cache past year monthly sales of every company based on sales invoices"""
	import json

	from frappe.utils.goal import get_monthly_results

	filter_str = "company = {0} and status != 'Draft' and docstatus=1".format(
		frappe.db.escape(company)
	)
	month_to_value_dict = get_monthly_results(
		"Sales Invoice", "base_grand_total", "posting_date", filter_str, "sum"
	)

	frappe.db.set_value("Company", company, "sales_monthly_history", json.dumps(month_to_value_dict))


def update_transactions_annual_history(company, commit=False):
	transactions_history = get_all_transactions_annual_history(company)
	frappe.db.set_value(
		"Company", company, "transactions_annual_history", json.dumps(transactions_history)
	)

	if commit:
		frappe.db.commit()


def cache_companies_monthly_sales_history():
	companies = [d["name"] for d in frappe.get_list("Company")]
	for company in companies:
		update_company_monthly_sales(company)
		update_transactions_annual_history(company)
	frappe.db.commit()


def get_all_transactions_annual_history(company):
	out = {}

	items = frappe.db.sql(
		"""
		select transaction_date, count(*) as count

		from (
			select name, transaction_date, company
			from `tabQuotation`

			UNION ALL

			select name, transaction_date, company
			from `tabSales Order`

			UNION ALL

			select name, posting_date as transaction_date, company
			from `tabDelivery Note`

			UNION ALL

			select name, posting_date as transaction_date, company
			from `tabSales Invoice`

			UNION ALL

			select name, creation as transaction_date, company
			from `tabIssue`

			UNION ALL

			select name, creation as transaction_date, company
			from `tabProject`
		) t

		where
			company=%s
			and
			transaction_date > date_sub(curdate(), interval 1 year)

		group by
			transaction_date
			""",
		(company),
		as_dict=True,
	)

	for d in items:
		timestamp = get_timestamp(d["transaction_date"])
		out.update({timestamp: d["count"]})

	return out


def get_timeline_data(doctype, name):
	"""returns timeline data based on linked records in dashboard"""
	out = {}
	date_to_value_dict = {}

	history = frappe.get_cached_value("Company", name, "transactions_annual_history")

	try:
		date_to_value_dict = json.loads(history) if history and "{" in history else None
	except ValueError:
		date_to_value_dict = None

	if date_to_value_dict is None:
		update_transactions_annual_history(name, True)
		history = frappe.get_cached_value("Company", name, "transactions_annual_history")
		return json.loads(history) if history and "{" in history else {}

	return date_to_value_dict


@frappe.whitelist()
def create_transaction_deletion_request(company):
	tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": company})
	tdr.insert()
	tdr.submit()
