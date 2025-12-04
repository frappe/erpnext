# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json

import frappe
import frappe.defaults
from frappe import _, bold
from frappe.cache_manager import clear_defaults_cache
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.desk.page.setup_wizard.setup_wizard import make_records
from frappe.utils import add_months, cint, formatdate, get_first_day, get_link_to_form, get_timestamp, today
from frappe.utils.nestedset import NestedSet, rebuild_tree

from erpnext.accounts.doctype.account.account import get_account_currency
from erpnext.accounts.doctype.financial_report_template.financial_report_template import (
	sync_financial_report_templates,
)
from erpnext.setup.setup_wizard.operations.taxes_setup import setup_taxes_and_charges
from erpnext.stock.utils import check_pending_reposting


class Company(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		abbr: DF.Data
		accounts_frozen_till_date: DF.Date | None
		accumulated_depreciation_account: DF.Link | None
		allow_account_creation_against_child_company: DF.Check
		asset_received_but_not_billed: DF.Link | None
		auto_err_frequency: DF.Literal["Daily", "Weekly", "Monthly"]
		auto_exchange_rate_revaluation: DF.Check
		book_advance_payments_in_separate_party_account: DF.Check
		capital_work_in_progress_account: DF.Link | None
		chart_of_accounts: DF.Literal[None]
		company_description: DF.TextEditor | None
		company_logo: DF.AttachImage | None
		company_name: DF.Data
		cost_center: DF.Link | None
		country: DF.Link
		create_chart_of_accounts_based_on: DF.Literal["", "Standard Template", "Existing Company"]
		credit_limit: DF.Currency
		date_of_commencement: DF.Date | None
		date_of_establishment: DF.Date | None
		date_of_incorporation: DF.Date | None
		default_advance_paid_account: DF.Link | None
		default_advance_received_account: DF.Link | None
		default_bank_account: DF.Link | None
		default_buying_terms: DF.Link | None
		default_cash_account: DF.Link | None
		default_currency: DF.Link
		default_deferred_expense_account: DF.Link | None
		default_deferred_revenue_account: DF.Link | None
		default_discount_account: DF.Link | None
		default_expense_account: DF.Link | None
		default_fg_warehouse: DF.Link | None
		default_finance_book: DF.Link | None
		default_holiday_list: DF.Link | None
		default_in_transit_warehouse: DF.Link | None
		default_income_account: DF.Link | None
		default_inventory_account: DF.Link | None
		default_letter_head: DF.Link | None
		default_operating_cost_account: DF.Link | None
		default_payable_account: DF.Link | None
		default_provisional_account: DF.Link | None
		default_receivable_account: DF.Link | None
		default_sales_contact: DF.Link | None
		default_scrap_warehouse: DF.Link | None
		default_selling_terms: DF.Link | None
		default_warehouse_for_sales_return: DF.Link | None
		default_wip_warehouse: DF.Link | None
		depreciation_cost_center: DF.Link | None
		depreciation_expense_account: DF.Link | None
		disposal_account: DF.Link | None
		domain: DF.Data | None
		email: DF.Data | None
		enable_item_wise_inventory_account: DF.Check
		enable_perpetual_inventory: DF.Check
		enable_provisional_accounting_for_non_stock_items: DF.Check
		exception_budget_approver_role: DF.Link | None
		exchange_gain_loss_account: DF.Link | None
		existing_company: DF.Link | None
		fax: DF.Data | None
		is_group: DF.Check
		lft: DF.Int
		monthly_sales_target: DF.Currency
		old_parent: DF.Data | None
		parent_company: DF.Link | None
		payment_terms: DF.Link | None
		phone_no: DF.Data | None
		purchase_expense_account: DF.Link | None
		purchase_expense_contra_account: DF.Link | None
		reconcile_on_advance_payment_date: DF.Check
		reconciliation_takes_effect_on: DF.Literal[
			"Advance Payment Date", "Oldest Of Invoice Or Advance", "Reconciliation Date"
		]
		registration_details: DF.Code | None
		reporting_currency: DF.Link | None
		rgt: DF.Int
		role_allowed_for_frozen_entries: DF.Link | None
		round_off_account: DF.Link | None
		round_off_cost_center: DF.Link | None
		round_off_for_opening: DF.Link | None
		sales_monthly_history: DF.SmallText | None
		series_for_depreciation_entry: DF.Data | None
		service_expense_account: DF.Link | None
		stock_adjustment_account: DF.Link | None
		stock_received_but_not_billed: DF.Link | None
		submit_err_jv: DF.Check
		tax_id: DF.Data | None
		total_monthly_sales: DF.Currency
		transactions_annual_history: DF.Code | None
		unrealized_exchange_gain_loss_account: DF.Link | None
		unrealized_profit_loss_account: DF.Link | None
		valuation_method: DF.Literal["FIFO", "Moving Average", "LIFO"]
		website: DF.Data | None
		write_off_account: DF.Link | None
	# end: auto-generated types

	nsm_parent_field = "parent_company"

	def onload(self):
		load_address_and_contact(self, "company")

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
			if frappe.db.sql(
				"""select name from `tab{}` where company={} and docstatus=1
					limit 1""".format(doctype, "%s"),
				self.name,
			):
				exists = True
				break

		return exists

	def validate(self):
		old_doc = self.get_doc_before_save()
		self.update_default_account = False
		if self.is_new():
			self.update_default_account = True

		self.validate_abbr()
		self.validate_default_accounts()
		self.validate_currency()
		self.validate_advance_account_currency()
		self.validate_coa_input()
		self.validate_perpetual_inventory()
		self.validate_provisional_account_for_non_stock_items()
		self.check_country_change()
		self.check_parent_changed()
		self.set_chart_of_accounts()
		self.validate_parent_company()
		self.set_reporting_currency()
		self.validate_inventory_account_settings()
		self.cant_change_valuation_method()
		self.validate_pending_reposts(old_doc)

	def cant_change_valuation_method(self):
		doc_before_save = self.get_doc_before_save()
		if not doc_before_save:
			return

		previous_valuation_method = doc_before_save.get("valuation_method")

		if previous_valuation_method and previous_valuation_method != self.valuation_method:
			# check if there are any stock ledger entries against items
			# which does not have it's own valuation method
			sle = frappe.db.sql(
				"""select name from `tabStock Ledger Entry` sle
				where exists(select name from tabItem
					where name=sle.item_code and (valuation_method is null or valuation_method='')) and sle.company=%s limit 1
			""",
				self.name,
			)

			if sle:
				frappe.throw(
					_(
						"Can't change the valuation method, as there are transactions against some items which do not have its own valuation method"
					)
				)

	def validate_inventory_account_settings(self):
		doc_before_save = self.get_doc_before_save()
		if not doc_before_save:
			return

		if (
			doc_before_save.enable_item_wise_inventory_account != self.enable_item_wise_inventory_account
			and frappe.db.get_value("Stock Ledger Entry", {"is_cancelled": 0, "company": self.name}, "name")
			and doc_before_save.enable_perpetual_inventory
		):
			frappe.throw(
				_(
					"Cannot enable Item-wise Inventory Account, as there are existing Stock Ledger Entries for the company {0} with Warehouse-wise Inventory Account. Please cancel the stock transactions first and try again."
				).format(bold(self.name)),
				title=_("Cannot Change Inventory Account Setting"),
			)

	def validate_abbr(self):
		if not self.abbr:
			self.abbr = "".join(c[0] for c in self.company_name.split()).upper()

		self.abbr = self.abbr.strip()

		if not self.abbr.strip():
			frappe.throw(_("Abbreviation is mandatory"))

		if frappe.db.sql("select abbr from tabCompany where name!=%s and abbr=%s", (self.name, self.abbr)):
			frappe.throw(_("Abbreviation already used for another company"))

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
			["Write Off Account", "write_off_account"],
			["Default Payment Discount Account", "default_discount_account"],
			["Unrealized Profit / Loss Account", "unrealized_profit_loss_account"],
			["Exchange Gain / Loss Account", "exchange_gain_loss_account"],
			["Unrealized Exchange Gain / Loss Account", "unrealized_exchange_gain_loss_account"],
			["Round Off Account", "round_off_account"],
			["Default Deferred Revenue Account", "default_deferred_revenue_account"],
			["Default Deferred Expense Account", "default_deferred_expense_account"],
			["Accumulated Depreciation Account", "accumulated_depreciation_account"],
			["Depreciation Expense Account", "depreciation_expense_account"],
			["Gain/Loss Account on Asset Disposal", "disposal_account"],
		]

		for account in accounts:
			if self.get(account[1]):
				for_company, is_group, disabled = frappe.db.get_value(
					"Account", self.get(account[1]), ["company", "is_group", "disabled"]
				)

				if disabled:
					frappe.throw(_("Account {0} is disabled.").format(frappe.bold(self.get(account[1]))))

				if is_group:
					frappe.throw(
						_("{0}: {1} is a group account.").format(
							frappe.bold(account[0]), frappe.bold(self.get(account[1]))
						)
					)

				if for_company != self.name:
					frappe.throw(
						_("Account {0} does not belong to company: {1}").format(
							self.get(account[1]), self.name
						)
					)

				if get_account_currency(self.get(account[1])) != self.default_currency:
					error_message = _(
						"{0} currency must be same as company's default currency. Please select another account."
					).format(frappe.bold(account[0]))
					frappe.throw(error_message)

	def validate_advance_account_currency(self):
		if (
			self.default_advance_received_account
			and frappe.get_cached_value("Account", self.default_advance_received_account, "account_currency")
			!= self.default_currency
		):
			frappe.throw(
				_("'{0}' should be in company currency {1}.").format(
					frappe.bold(_("Default Advance Received Account")), frappe.bold(self.default_currency)
				)
			)

		if (
			self.default_advance_paid_account
			and frappe.get_cached_value("Account", self.default_advance_paid_account, "account_currency")
			!= self.default_currency
		):
			frappe.throw(
				_("'{0}' should be in company currency {1}.").format(
					frappe.bold(_("Default Advance Paid Account")), frappe.bold(self.default_currency)
				)
			)

	def validate_currency(self):
		if self.is_new():
			return
		self.previous_default_currency = frappe.get_cached_value("Company", self.name, "default_currency")
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
		if not frappe.db.sql(
			"""select name from tabAccount
				where company=%s and docstatus<2 limit 1""",
			self.name,
		):
			if not frappe.local.flags.ignore_chart_of_accounts:
				frappe.flags.country_change = True
				sync_financial_report_templates(self.chart_of_accounts, self.existing_company)
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

		if self.default_currency:
			frappe.db.set_value("Currency", self.default_currency, "enabled", 1)

		if (
			hasattr(frappe.local, "enable_perpetual_inventory")
			and self.name in frappe.local.enable_perpetual_inventory
		):
			frappe.local.enable_perpetual_inventory[self.name] = self.enable_perpetual_inventory

		if frappe.flags.parent_company_changed:
			from frappe.utils.nestedset import rebuild_tree

			rebuild_tree("Company")

		frappe.clear_cache()

	def create_default_warehouses(self):
		parent_warehouse = None
		for wh_detail in [
			{"warehouse_name": _("All Warehouses"), "is_group": 1},
			{"warehouse_name": _("Stores"), "is_group": 0},
			{"warehouse_name": _("Work In Progress"), "is_group": 0},
			{"warehouse_name": _("Finished Goods"), "is_group": 0},
			{"warehouse_name": _("Goods In Transit"), "is_group": 0, "warehouse_type": "Transit"},
		]:
			if frappe.db.exists(
				"Warehouse",
				{
					"warehouse_name": wh_detail["warehouse_name"],
					"company": self.name,
				},
			):
				continue

			warehouse = frappe.get_doc(
				{
					"doctype": "Warehouse",
					"warehouse_name": wh_detail["warehouse_name"],
					"is_group": wh_detail["is_group"],
					"company": self.name,
					"parent_warehouse": parent_warehouse,
					"warehouse_type": wh_detail.get("warehouse_type"),
				}
			)
			warehouse.flags.ignore_permissions = True
			warehouse.flags.ignore_mandatory = True
			warehouse.insert()

			if wh_detail["is_group"]:
				parent_warehouse = warehouse.name

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
			frappe.db.get_value("Account", {"company": self.name, "account_type": "Payable", "is_group": 0}),
		)

	def create_default_departments(self):
		records = [
			# Department
			{
				"doctype": "Department",
				"department_name": _("All Departments"),
				"is_group": 1,
				"parent_department": "",
				"__condition": lambda: not frappe.db.exists("Department", _("All Departments")),
			},
			{
				"doctype": "Department",
				"department_name": _("Accounts"),
				"parent_department": _("All Departments"),
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Marketing"),
				"parent_department": _("All Departments"),
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Sales"),
				"parent_department": _("All Departments"),
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Purchase"),
				"parent_department": _("All Departments"),
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Operations"),
				"parent_department": _("All Departments"),
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Production"),
				"parent_department": _("All Departments"),
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Dispatch"),
				"parent_department": _("All Departments"),
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Customer Service"),
				"parent_department": _("All Departments"),
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Human Resources"),
				"parent_department": _("All Departments"),
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Management"),
				"parent_department": _("All Departments"),
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Quality Management"),
				"parent_department": _("All Departments"),
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Research & Development"),
				"parent_department": _("All Departments"),
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Legal"),
				"parent_department": _("All Departments"),
				"company": self.name,
			},
		]

		# Make root department with NSM updation
		make_records(records[:1])

		frappe.local.flags.ignore_update_nsm = True
		make_records(records)
		frappe.local.flags.ignore_update_nsm = False
		rebuild_tree("Department")

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

		doc_before_save = self.get_doc_before_save()
		if not doc_before_save:
			return

		if (
			doc_before_save.enable_perpetual_inventory
			and not self.enable_perpetual_inventory
			and doc_before_save.enable_item_wise_inventory_account != self.enable_item_wise_inventory_account
		):
			if frappe.db.get_value("Stock Ledger Entry", {"is_cancelled": 0, "company": self.name}, "name"):
				frappe.throw(
					_(
						"Cannot disable perpetual inventory, as there are existing Stock Ledger Entries for the company {0}. Please cancel the stock transactions first and try again."
					).format(bold(self.name))
				)

	def validate_provisional_account_for_non_stock_items(self):
		if not self.get("__islocal"):
			if (
				cint(self.enable_provisional_accounting_for_non_stock_items) == 1
				and not self.default_provisional_account
			):
				frappe.throw(
					_("Set default {0} account for non stock items").format(
						frappe.bold(_("Provisional Account"))
					)
				)

			make_property_setter(
				"Purchase Receipt",
				"provisional_expense_account",
				"hidden",
				not self.enable_provisional_accounting_for_non_stock_items,
				"Check",
				validate_fields_for_doctype=False,
			)

	def check_country_change(self):
		frappe.flags.country_change = False

		if not self.is_new() and self.country != frappe.get_cached_value("Company", self.name, "country"):
			frappe.flags.country_change = True

	def set_chart_of_accounts(self):
		"""If parent company is set, chart of accounts will be based on that company"""
		if self.parent_company:
			self.create_chart_of_accounts_based_on = "Existing Company"
			self.existing_company = self.parent_company

	def validate_parent_company(self):
		if self.parent_company:
			is_group = frappe.get_value("Company", self.parent_company, "is_group")

			if not is_group:
				frappe.throw(_("Parent Company must be a group company"))

	def set_reporting_currency(self):
		self.reporting_currency = self.default_currency
		if self.parent_company:
			parent_reporting_currency = frappe.db.get_value(
				"Company", self.parent_company, ["reporting_currency"]
			)
			self.reporting_currency = parent_reporting_currency

	def validate_pending_reposts(self, old_doc):
		if old_doc and old_doc.accounts_frozen_till_date != self.accounts_frozen_till_date:
			if self.accounts_frozen_till_date:
				check_pending_reposting(self.accounts_frozen_till_date, self.name)

	def set_default_accounts(self):
		default_accounts = {
			"default_cash_account": "Cash",
			"default_bank_account": "Bank",
			"round_off_account": "Round Off",
			"accumulated_depreciation_account": "Accumulated Depreciation",
			"depreciation_expense_account": "Depreciation",
			"capital_work_in_progress_account": "Capital Work in Progress",
			"asset_received_but_not_billed": "Asset Received But Not Billed",
			"default_expense_account": "Cost of Goods Sold",
		}

		if self.enable_perpetual_inventory:
			default_accounts.update(
				{
					"stock_received_but_not_billed": "Stock Received But Not Billed",
					"default_inventory_account": "Stock",
					"stock_adjustment_account": "Stock Adjustment",
				}
			)

		if self.update_default_account:
			for default_account in default_accounts:
				self._set_default_account(default_account, default_accounts.get(default_account))

		if not self.default_income_account:
			income_account = frappe.db.get_all(
				"Account",
				filters={"company": self.name, "is_group": 0},
				or_filters={
					"account_name": ("in", [_("Sales"), _("Sales Account")]),
					"account_type": "Income Account",
				},
				pluck="name",
			)

			if income_account:
				income_account = income_account[0]
			else:
				income_account = None

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

		if not self.service_expense_account:
			service_expense_acct = frappe.db.get_value(
				"Account",
				{
					"account_name": _("Marketing Expenses"),
					"company": self.name,
					"is_group": 0,
					"root_type": "Expense",
				},
				"name",
			)

			if service_expense_acct:
				self.db_set("service_expense_account", service_expense_acct)

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

	def after_rename(self, olddn, newdn, merge=False):
		self.db_set("company_name", newdn)

		frappe.db.sql(
			"""update `tabDefaultValue` set defvalue=%s
			where defkey='Company' and defvalue=%s""",
			(newdn, olddn),
		)

		clear_defaults_cache()

	def abbreviate(self):
		self.abbr = "".join(c[0].upper() for c in self.company_name.split())

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
				frappe.db.sql(f"delete from `tab{doctype}` where company = %s", self.name)

		if not frappe.db.get_value("Stock Ledger Entry", {"company": self.name}):
			frappe.db.sql("""delete from `tabWarehouse` where company=%s""", self.name)

		frappe.defaults.clear_default("company", value=self.name)
		for doctype in ["Mode of Payment Account", "Item Default"]:
			frappe.db.sql(f"delete from `tab{doctype}` where company = %s", self.name)

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
					"delete from `tab{}` where parent in ({})".format(dt, ", ".join(["%s"] * len(boms))),
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

	def check_parent_changed(self):
		frappe.flags.parent_company_changed = False

		if not self.is_new() and self.parent_company != frappe.db.get_value(
			"Company", self.name, "parent_company"
		):
			frappe.flags.parent_company_changed = True


def get_name_with_abbr(name, company):
	company_abbr = frappe.get_cached_value("Company", company, "abbr")
	parts = name.split(" - ")

	if parts[-1].lower() != company_abbr.lower():
		parts.append(company_abbr)

	return " - ".join(parts)


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
	from_date = get_first_day(today())
	to_date = get_first_day(add_months(from_date, 1))

	results = frappe.db.sql(
		"""
		SELECT
			SUM(base_grand_total) AS total,
			DATE_FORMAT(posting_date, '%%m-%%Y') AS month_year
		FROM
			`tabSales Invoice`
		WHERE
			posting_date >= %s
			AND posting_date < %s
			AND docstatus = 1
			AND company = %s
		GROUP BY
			month_year
		""",
		(from_date, to_date, company),
		as_dict=True,
	)

	monthly_total = results[0]["total"] if len(results) > 0 else 0
	frappe.db.set_value("Company", company, "total_monthly_sales", monthly_total)


def update_company_monthly_sales(company):
	"""Cache past year monthly sales of every company based on sales invoices"""
	from frappe.utils.goal import get_monthly_results

	filter_dict = {"company": company, "status": ["!=", "Draft"], "docstatus": 1}
	month_to_value_dict = get_monthly_results(
		"Sales Invoice", "base_grand_total", "posting_date", filter_dict, "sum"
	)

	frappe.db.set_value("Company", company, "sales_monthly_history", json.dumps(month_to_value_dict))


def update_transactions_annual_history(company, commit=False):
	transactions_history = get_all_transactions_annual_history(company)
	frappe.db.set_value("Company", company, "transactions_annual_history", json.dumps(transactions_history))

	if commit:
		frappe.db.commit()


def cache_companies_monthly_sales_history():
	companies = [d["name"] for d in frappe.get_list("Company")]
	for company in companies:
		update_company_monthly_sales(company)
		update_transactions_annual_history(company)
	frappe.db.commit()


@frappe.whitelist()
def get_children(doctype, parent=None, company=None, is_root=False):
	if parent is None or parent == "All Companies":
		parent = ""

	return frappe.db.sql(
		f"""
		select
			name as value,
			is_group as expandable
		from
			`tabCompany` comp
		where
			ifnull(parent_company, "")={frappe.db.escape(parent)}
		""",
		as_dict=1,
	)


@frappe.whitelist()
def add_node():
	from frappe.desk.treeview import make_tree_args

	args = frappe.form_dict
	args = make_tree_args(**args)

	if args.parent_company == "All Companies":
		args.parent_company = None

	frappe.get_doc(args).insert()


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
def get_default_company_address(name, sort_key="is_primary_address", existing_address=None):
	if sort_key not in ["is_shipping_address", "is_primary_address"]:
		return None

	out = frappe.db.sql(
		""" SELECT
			addr.name, addr.{}
		FROM
			`tabAddress` addr, `tabDynamic Link` dl
		WHERE
			dl.parent = addr.name and dl.link_doctype = 'Company' and
			dl.link_name = {} and ifnull(addr.disabled, 0) = 0
		""".format(sort_key, "%s"),
		(name),
	)  # nosec

	if existing_address:
		if existing_address in [d[0] for d in out]:
			return existing_address

	if out:
		return max(out, key=lambda x: x[1])[0]  # find max by sort_key
	else:
		return None


@frappe.whitelist()
def get_billing_shipping_address(name, billing_address=None, shipping_address=None):
	primary_address = get_default_company_address(name, "is_primary_address", billing_address)
	shipping_address = get_default_company_address(name, "is_shipping_address", shipping_address)

	return {"primary_address": primary_address, "shipping_address": shipping_address}


@frappe.whitelist()
def create_transaction_deletion_request(company):
	from erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record import (
		is_deletion_doc_running,
	)

	is_deletion_doc_running(company)

	tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": company})
	tdr.submit()
	tdr.start_deletion_tasks()

	frappe.msgprint(
		_("A Transaction Deletion Document: {0} is triggered for {0}").format(
			get_link_to_form("Transaction Deletion Record", tdr.name)
		),
		frappe.bold(company),
	)
