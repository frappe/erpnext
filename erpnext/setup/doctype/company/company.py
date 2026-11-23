# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import json
from collections import Counter
from typing import Literal

import frappe
import frappe.defaults
from frappe import _, bold
from frappe.cache_manager import clear_defaults_cache
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.desk.page.setup_wizard.setup_wizard import make_records
from frappe.utils import (
	add_to_date,
	cint,
	get_first_day,
	get_last_day,
	get_link_to_form,
	get_timestamp,
	nowdate,
	today,
)
from frappe.utils.nestedset import NestedSet, get_root_of, rebuild_tree

from erpnext.accounts.default_accounts import (
	ASSET_DISPOSAL,
	BANK_CHARGES,
	CASH,
	EXCHANGE_GAIN,
	EXCHANGE_GAIN_LOSS,
	EXCHANGE_LOSS,
	INCOME,
	INVENTORY,
	PAYABLE,
	PROVISIONAL,
	RECEIVABLE,
	STOCK_DELIVERED_BUT_NOT_BILLED,
	WRITE_OFF,
	get_purpose,
	get_purposes,
)
from erpnext.accounts.doctype.account.account import get_account_currency
from erpnext.accounts.doctype.financial_report_template.financial_report_template import (
	sync_financial_report_templates,
)
from erpnext.setup.doctype.terms_and_conditions.terms_and_conditions import validate_terms_and_conditions
from erpnext.setup.setup_wizard.operations.taxes_setup import setup_taxes_and_charges
from erpnext.stock.utils import check_pending_reposting


class Company(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.setup.doctype.company_default_account.company_default_account import (
			CompanyDefaultAccount,
		)

		abbr: DF.Data
		accounts_frozen_till_date: DF.Date | None
		allow_account_creation_against_child_company: DF.Check
		auto_err_frequency: DF.Literal["Daily", "Weekly", "Monthly"]
		auto_exchange_rate_revaluation: DF.Check
		book_advance_payments_in_separate_party_account: DF.Check
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
		default_accounts: DF.Table[CompanyDefaultAccount]
		default_buying_terms: DF.Link | None
		default_currency: DF.Link
		default_fg_warehouse: DF.Link | None
		default_finance_book: DF.Link | None
		default_holiday_list: DF.Link | None
		default_in_transit_warehouse: DF.Link | None
		default_letter_head: DF.Link | None
		default_letter_head_report: DF.Link | None
		default_sales_contact: DF.Link | None
		default_scrap_warehouse: DF.Link | None
		default_selling_terms: DF.Link | None
		default_warehouse: DF.Link | None
		default_warehouse_for_sales_return: DF.Link | None
		default_wip_warehouse: DF.Link | None
		depreciation_cost_center: DF.Link | None
		disable_sdbnb_in_sr: DF.Check
		domain: DF.Data | None
		email: DF.Data | None
		enable_item_wise_inventory_account: DF.Check
		enable_perpetual_inventory: DF.Check
		enable_provisional_accounting_for_non_stock_items: DF.Check
		enable_stock_delivered_but_not_billed: DF.Check
		exception_budget_approver_role: DF.Link | None
		existing_company: DF.Link | None
		fax: DF.Data | None
		is_group: DF.Check
		lft: DF.Int
		monthly_sales_target: DF.Currency
		old_parent: DF.Data | None
		parent_company: DF.Link | None
		payment_terms: DF.Link | None
		phone_no: DF.Data | None
		reconcile_on_advance_payment_date: DF.Check
		reconciliation_takes_effect_on: DF.Literal[
			"Advance Payment Date", "Oldest Of Invoice Or Advance", "Reconciliation Date"
		]
		registration_details: DF.Code | None
		reporting_currency: DF.Link | None
		rgt: DF.Int
		role_allowed_for_frozen_entries: DF.Link | None
		round_off_cost_center: DF.Link | None
		sales_monthly_history: DF.SmallText | None
		sample_retention_warehouse: DF.Link | None
		series_for_depreciation_entry: DF.Data | None
		submit_err_jv: DF.Check
		tax_id: DF.Data | None
		total_monthly_sales: DF.Currency
		transactions_annual_history: DF.Code | None
		valuation_method: DF.Literal["FIFO", "Moving Average", "LIFO"]
		website: DF.Data | None
	# end: auto-generated types

	nsm_parent_field = "parent_company"

	def onload(self):
		load_address_and_contact(self, "company")

	@frappe.whitelist()
	def check_if_transactions_exist(self):
		if frappe.db.exists("GL Entry", {"company": self.name, "is_cancelled": 0}) or frappe.db.exists(
			"Stock Ledger Entry", {"company": self.name, "is_cancelled": 0}
		):
			return True

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
			if frappe.db.exists(doctype, {"company": self.name, "docstatus": 1}):
				exists = True
				break

		return exists

	def validate(self):
		old_doc = self.get_doc_before_save()
		for field, module in (("default_selling_terms", "selling"), ("default_buying_terms", "buying")):
			if not old_doc or self.get(field) != old_doc.get(field):
				validate_terms_and_conditions(self.get(field), module)
		self.update_default_account = False
		if self.is_new():
			self.update_default_account = True

		self.validate_abbr()
		self.validate_currency()
		self.validate_default_accounts()
		self.validate_coa_input()
		self.validate_perpetual_inventory()
		self.validate_provisional_account_for_non_stock_items()
		self.check_country_change()
		self.check_parent_changed()
		self.set_chart_of_accounts()
		self.validate_parent_company()
		self.set_reporting_currency()
		self.validate_inventory_account_settings()
		self.validate_warehouses()
		self.cant_change_valuation_method()
		self.validate_pending_reposts(old_doc)
		self.validate_sdbnb_configuration()

	def validate_outstanding_sdbnb_transactions(self, account):
		GLEntry = frappe.qb.DocType("GL Entry")
		DeliveryNote = frappe.qb.DocType("Delivery Note")

		delivery_notes = (
			frappe.qb.from_(GLEntry)
			.join(DeliveryNote)
			.on((GLEntry.voucher_type == "Delivery Note") & (GLEntry.voucher_no == DeliveryNote.name))
			.select(DeliveryNote.name)
			.where(
				(GLEntry.is_cancelled == 0)
				& (GLEntry.company == self.name)
				& (GLEntry.account == account)
				& (DeliveryNote.per_billed < 100)
				& (DeliveryNote.docstatus == 1)
				& (DeliveryNote.status.isin(["To Bill", "Partially Billed"]))
			)
			.distinct()
			.run(pluck=True)
		)

		if delivery_notes:
			dn_links = ", ".join(get_link_to_form("Delivery Note", dn) for dn in delivery_notes[:10])

			frappe.throw(
				_(
					"Stock Delivered But Not Billed Account cannot be changed or disabled since account {0} contains outstanding Delivery Notes: {1}"
				).format(
					bold(account),
					dn_links,
				)
			)

	def validate_sdbnb_configuration(self):
		if self.get("__islocal"):
			return

		sdbnb_account = self.get_default_account(STOCK_DELIVERED_BUT_NOT_BILLED)
		if self.enable_stock_delivered_but_not_billed and not sdbnb_account:
			frappe.throw(_("Please select Stock Delivered But Not Billed Account"))

		doc_before_save = self.get_doc_before_save()
		if not doc_before_save:
			return

		old_sdbnb_account = doc_before_save.get_default_account(STOCK_DELIVERED_BUT_NOT_BILLED)
		if not old_sdbnb_account:
			return

		account_changed = sdbnb_account != old_sdbnb_account

		feature_disabled = (
			doc_before_save.enable_stock_delivered_but_not_billed
			and not self.enable_stock_delivered_but_not_billed
		)

		if account_changed or feature_disabled:
			self.validate_outstanding_sdbnb_transactions(old_sdbnb_account)

	def cant_change_valuation_method(self):
		doc_before_save = self.get_doc_before_save()
		if not doc_before_save:
			return

		previous_valuation_method = doc_before_save.get("valuation_method")

		if previous_valuation_method and previous_valuation_method != self.valuation_method:
			# check if there are any stock ledger entries against items
			# which does not have it's own valuation method
			sle_dt = frappe.qb.DocType("Stock Ledger Entry")
			item = frappe.qb.DocType("Item")
			sle = (
				frappe.qb.from_(sle_dt)
				.select(sle_dt.name)
				.where(
					(sle_dt.company == self.name)
					& sle_dt.item_code.isin(
						frappe.qb.from_(item)
						.select(item.name)
						.where(item.valuation_method.isnull() | (item.valuation_method == ""))
					)
				)
				.limit(1)
				.run()
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

	def validate_warehouses(self):
		for fieldname in (
			"default_warehouse",
			"sample_retention_warehouse",
			"default_in_transit_warehouse",
			"default_warehouse_for_sales_return",
			"default_wip_warehouse",
			"default_fg_warehouse",
			"default_scrap_warehouse",
		):
			warehouse = self.get(fieldname)
			if not warehouse:
				continue

			details = frappe.db.get_value(
				"Warehouse", warehouse, ["is_group", "company", "disabled", "warehouse_type"], as_dict=True
			)
			if not details:
				continue

			label = self.meta.get_translated_label(fieldname)

			if details.is_group:
				frappe.throw(
					_(
						"Group Warehouses cannot be used in transactions. Please change the value of {0}"
					).format(bold(label)),
					title=_("Incorrect Warehouse"),
				)

			if details.company != self.name:
				frappe.throw(
					_("{0} {1} does not belong to company {2}").format(
						bold(label), bold(warehouse), bold(self.name)
					),
					title=_("Incorrect Warehouse"),
				)

			if not self.is_value_new_or_changed(fieldname):
				continue

			if details.disabled:
				frappe.throw(_("{0} {1} is disabled").format(bold(label), bold(warehouse)))

			if fieldname == "default_in_transit_warehouse" and details.warehouse_type != "Transit":
				frappe.throw(_("{0} must be a Transit Warehouse").format(bold(label)))

	def validate_abbr(self):
		if not self.abbr:
			self.abbr = "".join(c[0] for c in self.company_name.split()).upper()

		self.abbr = self.abbr.strip()

		if not self.abbr.strip():
			frappe.throw(_("Abbreviation is mandatory"))

		if frappe.db.exists("Company", {"name": ["!=", self.name], "abbr": self.abbr}):
			frappe.throw(_("Abbreviation already used for another company"))

	@frappe.whitelist()
	def create_default_tax_template(self):
		frappe.only_for(("System Manager", "Accounts Manager"))
		setup_taxes_and_charges(self.name, self.country)

	def validate_default_accounts(self):
		purposes = get_purposes()
		doc_before_save = self.get_doc_before_save()
		old_accounts = {}
		if doc_before_save:
			old_accounts = {row.purpose: row.account for row in doc_before_save.default_accounts}

		seen_purposes = set()
		for row in self.default_accounts:
			account_changed = old_accounts.get(row.purpose) != row.account
			purpose = purposes.get(row.purpose)
			# keep the unchanged rows of an uninstalled app
			if not purpose and row.purpose in old_accounts and not account_changed:
				continue

			if not purpose:
				frappe.throw(
					_("Row #{0}: {1} is not a valid default account purpose").format(
						row.idx, bold(row.purpose)
					)
				)

			label = _(purpose.label)
			if row.purpose in seen_purposes:
				frappe.throw(_("Row #{0}: {1} is set more than once").format(row.idx, bold(label)))
			seen_purposes.add(row.purpose)

			# the mandatory check runs after validate
			if not row.account:
				continue

			if account_changed:
				self.validate_default_account(row.account, label, purpose.filters)

			if account_changed or self.currency_changed:
				if get_account_currency(row.account) not in {
					self.default_currency,
					self.previous_default_currency,
				}:
					frappe.throw(
						_(
							"{0} currency must be same as company's default currency. Please select another account."
						).format(bold(label))
					)

		# show the rows in the order of the registry
		purpose_order = {key: index for index, key in enumerate(purposes)}
		self.default_accounts.sort(key=lambda row: purpose_order.get(row.purpose, len(purpose_order)))
		for idx, row in enumerate(self.default_accounts, start=1):
			row.idx = idx

		for fieldname in ("cost_center", "round_off_cost_center", "depreciation_cost_center"):
			cost_center = self.get(fieldname)
			if not cost_center or not self.is_value_new_or_changed(fieldname):
				continue

			company, is_group = frappe.db.get_value("Cost Center", cost_center, ["company", "is_group"])
			if company != self.name or is_group:
				frappe.throw(
					_("{0} must be a non-group Cost Center of {1}").format(
						self.meta.get_translated_label(fieldname), self.name
					)
				)

	def get_default_account(self, purpose: str, required: bool = False) -> str | None:
		"""Return the account of this purpose, else the account of its fallback purpose."""
		default_purpose = get_purpose(purpose)
		row = self.get_default_account_row(purpose)
		account = row.account if row else None
		if not account and default_purpose.fallback:
			account = self.get_default_account(default_purpose.fallback)

		if not account and required:
			frappe.throw(_("Please set {0} in Company {1}").format(_(default_purpose.label), self.name))

		return account

	def set_default_account(self, purpose: str, account: str | None) -> None:
		"""Set the account of this purpose. An empty account removes the row. The caller saves the Company."""
		get_purpose(purpose)
		row = self.get_default_account_row(purpose)
		if row and account:
			row.account = account
		elif row:
			self.remove(row)
		elif account:
			self.append("default_accounts", {"purpose": purpose, "account": account})

	def get_default_account_row(self, purpose: str):
		"""Return the row of this purpose in `default_accounts`, without fallback."""
		for row in self.default_accounts:
			if row.purpose == purpose:
				return row

	def is_value_new_or_changed(self, fieldname):
		"""Validate a default only when it is set, so existing defaults do not block unrelated saves."""
		return self.is_new() or self.has_value_changed(fieldname)

	def validate_default_account(self, account, label, filters):
		details = frappe.db.get_value(
			"Account",
			account,
			["company", "is_group", "disabled", "root_type", "account_type", "report_type"],
			as_dict=True,
		)

		if details.disabled:
			frappe.throw(_("Account {0} is disabled.").format(bold(account)))

		if details.is_group:
			frappe.throw(_("{0}: {1} is a group account.").format(bold(label), bold(account)))

		if details.company != self.name:
			frappe.throw(_("Account {0} does not belong to company: {1}").format(account, self.name))

		for key, expected in filters.items():
			# a filter value is a str or ["in", [...]]
			allowed_values = expected[1] if isinstance(expected, list) else [expected]
			if details.get(key) not in allowed_values:
				frappe.throw(_("{0}: {1} has an invalid {2}").format(label, account, key))

	def validate_currency(self):
		self.previous_default_currency = None
		self.currency_changed = False
		if self.is_new():
			return
		self.previous_default_currency = frappe.get_cached_value("Company", self.name, "default_currency")
		self.currency_changed = bool(
			self.default_currency
			and self.previous_default_currency
			and self.default_currency != self.previous_default_currency
		)
		if self.currency_changed and self.check_if_transactions_exist():
			frappe.throw(
				_(
					"Cannot change company's default currency, because there are existing transactions. Transactions must be cancelled to change the default currency."
				)
			)

	def on_update(self):
		NestedSet.on_update(self)
		if self.currency_changed:
			frappe.db.set_value(
				"Account",
				{"company": self.name, "account_currency": self.previous_default_currency},
				"account_currency",
				self.default_currency,
				update_modified=False,
			)
			frappe.local.cache.pop("account_currency", None)

		if not frappe.db.exists("Account", {"company": self.name, "docstatus": ["<", 2]}):
			if not frappe.local.flags.ignore_chart_of_accounts:
				frappe.flags.country_change = True
				sync_financial_report_templates(self.chart_of_accounts, self.existing_company)
				self.create_default_accounts()
				self.create_default_warehouses()

		if not frappe.db.get_value("Cost Center", {"is_group": 0, "company": self.name}):
			self.create_default_cost_center()

		if frappe.flags.country_change:
			install_country_fixtures(self.name, self.country)
			setup_taxes_and_charges(self.name, self.country)

		if not frappe.db.get_value("Department", {"company": self.name}):
			self.create_default_departments()

		if not frappe.local.flags.ignore_chart_of_accounts:
			self.set_default_accounts()
			if self.get_default_account(CASH):
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
			warehouse.flags.ignore_inventory_account_validation = True
			warehouse.insert()

			if wh_detail["is_group"]:
				parent_warehouse = warehouse.name

		if not self.default_warehouse:
			stores = frappe.db.get_value("Warehouse", {"warehouse_name": _("Stores"), "company": self.name})
			if stores:
				self.db_set("default_warehouse", stores)

	def create_default_accounts(self):
		from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import create_charts

		frappe.local.flags.ignore_root_company_validation = True
		create_charts(self.name, self.chart_of_accounts, self.existing_company)

		self.add_default_account_row(
			RECEIVABLE,
			frappe.db.get_value(
				"Account", {"company": self.name, "account_type": "Receivable", "is_group": 0}
			),
		)
		self.add_default_account_row(
			PAYABLE,
			frappe.db.get_value("Account", {"company": self.name, "account_type": "Payable", "is_group": 0}),
		)

	def create_default_departments(self):
		root = get_root_of("Department") or "All Departments"
		records = [
			# Department
			{
				"doctype": "Department",
				"department_name": root,
				"is_group": 1,
				"parent_department": "",
				"__condition": lambda: not frappe.db.exists("Department", root),
			},
			{
				"doctype": "Department",
				"department_name": _("Accounts"),
				"parent_department": root,
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Marketing"),
				"parent_department": root,
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Sales"),
				"parent_department": root,
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Purchase"),
				"parent_department": root,
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Operations"),
				"parent_department": root,
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Production"),
				"parent_department": root,
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Dispatch"),
				"parent_department": root,
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Customer Service"),
				"parent_department": root,
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Human Resources"),
				"parent_department": root,
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Management"),
				"parent_department": root,
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Quality Management"),
				"parent_department": root,
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Research & Development"),
				"parent_department": root,
				"company": self.name,
			},
			{
				"doctype": "Department",
				"department_name": _("Legal"),
				"parent_department": root,
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
			if cint(self.enable_perpetual_inventory) == 1 and not self.get_default_account(INVENTORY):
				frappe.msgprint(
					_("Set default inventory account for perpetual inventory"), alert=True, indicator="orange"
				)

		doc_before_save = self.get_doc_before_save()
		if not doc_before_save:
			return

		if doc_before_save.enable_perpetual_inventory and not self.enable_perpetual_inventory:
			if frappe.db.get_value("Stock Ledger Entry", {"is_cancelled": 0, "company": self.name}, "name"):
				frappe.throw(
					_(
						"Cannot disable perpetual inventory, as there are existing Stock Ledger Entries for the company {0}. Please cancel the stock transactions first and try again."
					).format(bold(self.name))
				)

	def validate_provisional_account_for_non_stock_items(self):
		if not self.get("__islocal"):
			provisional_enabled = cint(self.enable_provisional_accounting_for_non_stock_items) == 1
			if provisional_enabled and not self.get_default_account(PROVISIONAL):
				frappe.throw(
					_("Set default {0} account for non stock items").format(
						frappe.bold(_("Provisional Account"))
					)
				)

			self.set_provisional_expense_visibility(self.enable_provisional_accounting_for_non_stock_items)

	def set_provisional_expense_visibility(self, enabled):
		other_company_enabled = frappe.db.exists(
			"Company",
			{
				"name": ["!=", self.name],
				"enable_provisional_accounting_for_non_stock_items": 1,
			},
		)
		make_property_setter(
			"Purchase Receipt",
			"provisional_expense_account",
			"hidden",
			not (enabled or other_company_enabled),
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
		"""Find the default accounts of a new Company by account type and account name.

		This runs in `on_update`, so it writes each new row directly to the database.
		"""
		if not self.update_default_account:
			return

		for purpose in get_purposes().values():
			# a purpose of another app can have no Company field
			if not purpose.account_type or not purpose.fieldname:
				continue

			if purpose.depends_on and not self.get(purpose.depends_on):
				continue

			account = frappe.db.get_value(
				"Account", {"account_type": purpose.account_type, "is_group": 0, "company": self.name}
			)
			self.add_default_account_row(purpose.key, account)

		if not self.get_default_account_row(INCOME):
			income_accounts = frappe.db.get_all(
				"Account",
				filters={"company": self.name, "is_group": 0},
				or_filters={
					"account_name": ("in", [_("Sales"), _("Sales Account")]),
					"account_type": "Income Account",
				},
				pluck="name",
			)
			self.add_default_account_row(INCOME, income_accounts[0] if income_accounts else None)

		for purpose, account_name in (
			(WRITE_OFF, _("Write Off")),
			(BANK_CHARGES, _("Bank Charges")),
			(EXCHANGE_GAIN_LOSS, _("Exchange Gain/Loss")),
			(EXCHANGE_GAIN, _("Exchange Gain")),
			(EXCHANGE_LOSS, _("Exchange Loss")),
			(ASSET_DISPOSAL, _("Gain/Loss on Asset Disposal")),
		):
			account = frappe.db.get_value(
				"Account", {"account_name": account_name, "company": self.name, "is_group": 0}
			)
			self.add_default_account_row(purpose, account)

	def add_default_account_row(self, purpose: str, account: str | None) -> None:
		"""Add a row for this purpose in memory and in the database, unless the purpose has a row."""
		if not account or self.get_default_account_row(purpose):
			return

		row = self.append("default_accounts", {"purpose": purpose, "account": account})
		row.db_insert()

	def set_mode_of_payment_account(self):
		cash = frappe.db.get_value("Mode of Payment", {"type": "Cash"}, "name")
		cash_account = self.get_default_account(CASH)
		if (
			cash
			and cash_account
			and not frappe.db.get_value("Mode of Payment Account", {"company": self.name, "parent": cash})
		):
			mode_of_payment = frappe.get_doc("Mode of Payment", cash, for_update=True)
			mode_of_payment.append("accounts", {"company": self.name, "default_account": cash_account})
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

		default_value = frappe.qb.DocType("DefaultValue")
		(
			frappe.qb.update(default_value)
			.set(default_value.defvalue, newdn)
			.where((default_value.defkey == "Company") & (default_value.defvalue == olddn))
		).run()

		clear_defaults_cache()

	def abbreviate(self):
		self.abbr = "".join(c[0].upper() for c in self.company_name.split())

	def on_trash(self):
		"""
		Trash accounts and cost centers for this company if no gl entry exists
		"""
		if frappe.db.get_single_value("Global Defaults", "demo_company") == self.name:
			frappe.throw(
				_("{0} is the site's Demo Company and cannot be deleted directly. Use {1} instead.").format(
					bold(self.name), bold(_("Delete Demo Data"))
				)
			)

		NestedSet.validate_if_child_exists(self)
		for doctype in ("BOM", "Employee"):
			if frappe.db.exists(doctype, {"company": self.name}):
				frappe.throw(_("Cannot delete {0} while {1} records exist").format(self.name, doctype))
		frappe.utils.nestedset.update_nsm(self)

		warehouses = frappe.get_all("Warehouse", filters={"company": self.name}, pluck="name")
		if not frappe.db.exists("GL Entry", {"company": self.name}):
			budgets = frappe.get_all("Budget", filters={"company": self.name}, pluck="name")
			if budgets:
				frappe.db.delete("Budget Account", {"parent": ["in", budgets]})

			for doctype in ["Account", "Cost Center", "Budget", "Party Account"]:
				frappe.db.delete(doctype, {"company": self.name})

		if not frappe.db.get_value("Stock Ledger Entry", {"company": self.name}):
			if warehouses:
				frappe.db.delete("Item Reorder", {"warehouse": ["in", warehouses]})
				frappe.db.set_value(
					"Item Reorder", {"warehouse_group": ["in", warehouses]}, "warehouse_group", None
				)
			frappe.db.delete("Warehouse", {"company": self.name})

		frappe.defaults.clear_default("company", value=self.name)
		for doctype in ["Mode of Payment Account", "Item Default"]:
			frappe.db.delete(doctype, {"company": self.name})

		# reset default company
		singles = frappe.qb.DocType("Singles")
		(
			frappe.qb.update(singles)
			.set(singles.value, "")
			.where(
				(singles["doctype"] == "Global Defaults")
				& (singles.field == "default_company")
				& (singles.value == self.name)
			)
		).run()

		# reset default company
		(
			frappe.qb.update(singles)
			.set(singles.value, "")
			.where(
				(singles["doctype"] == "Chart of Accounts Importer")
				& (singles.field == "company")
				& (singles.value == self.name)
			)
		).run()

		frappe.db.delete("Department", {"company": self.name})
		frappe.db.delete("Tax Withholding Account", {"company": self.name})
		frappe.db.delete("Transaction Deletion Record", {"company": self.name})

		# Delete template details and item links with their parent templates.
		for template, child in (
			("Sales Taxes and Charges Template", "Sales Taxes and Charges"),
			("Purchase Taxes and Charges Template", "Purchase Taxes and Charges"),
			("Item Tax Template", "Item Tax Template Detail"),
		):
			names = frappe.get_all(template, filters={"company": self.name}, pluck="name")
			if names:
				if template == "Item Tax Template":
					frappe.db.delete("Item Tax", {"item_tax_template": ["in", names]})
				frappe.db.delete(child, {"parent": ["in", names], "parenttype": template})
				frappe.db.delete(template, {"name": ["in", names]})

		# delete Process Deferred Accounts if no GL Entry found
		if not frappe.db.get_value("GL Entry", {"company": self.name}):
			frappe.db.delete("Process Deferred Accounting", {"company": self.name})

		if self.enable_provisional_accounting_for_non_stock_items:
			self.set_provisional_expense_visibility(False)

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
		frappe.db.rollback()
		frappe.log_error("Unable to set country fixtures")
		frappe.throw(
			_("Failed to setup defaults for country {0}. Please contact support.").format(
				frappe.bold(country)
			)
		)


def update_company_current_month_sales(company):
	"""Update Company's Total Monthly Sales.

	Postgres compatibility:
	- Avoid MariaDB-only DATE_FORMAT().
	- Use a date range for the current month instead (portable + index-friendly).
	"""

	# Local imports so you don't have to touch file-level imports
	from frappe.query_builder.functions import Sum

	start_date = get_first_day(today())
	end_date = get_last_day(today())

	si = frappe.qb.DocType("Sales Invoice")

	total_monthly_sales = (
		frappe.qb.from_(si)
		.select(Sum(si.base_grand_total))
		.where(
			(si.docstatus == 1)
			& (si.company == company)
			& (si.is_opening != "Yes")
			& (si.posting_date >= start_date)
			& (si.posting_date <= end_date)
		)
	).run(pluck=True)[0] or 0

	# Fieldname in standard ERPNext is `total_monthly_sales`
	frappe.db.set_value(
		"Company",
		company,
		"total_monthly_sales",
		total_monthly_sales,
		update_modified=False,
	)


def update_company_monthly_sales(company):
	"""Cache past year monthly sales of every company based on sales invoices"""
	from frappe.utils.goal import get_monthly_results

	filter_dict = {"company": company, "status": ["!=", "Draft"], "docstatus": 1, "is_opening": ["!=", "Yes"]}
	month_to_value_dict = get_monthly_results(
		"Sales Invoice", "base_grand_total", "posting_date", filter_dict, "sum"
	)

	frappe.db.set_value("Company", company, "sales_monthly_history", json.dumps(month_to_value_dict))


def update_transactions_annual_history(company, commit=False):
	transactions_history = get_all_transactions_annual_history(company)
	frappe.db.set_value("Company", company, "transactions_annual_history", json.dumps(transactions_history))

	if commit and not frappe.in_test:
		# nosemgrep: frappe-semgrep-rules.rules.frappe-manual-commit -- background job saves progress or failure status
		frappe.db.commit()


def cache_companies_monthly_sales_history():
	refresh_total_monthly_sales = _should_refresh_total_monthly_sales()
	companies = [d["name"] for d in frappe.get_list("Company")]
	for company in companies:
		update_company_monthly_sales(company)
		update_transactions_annual_history(company)
		if refresh_total_monthly_sales:
			update_company_current_month_sales(company)

	if not frappe.in_test:
		# nosemgrep: frappe-semgrep-rules.rules.frappe-manual-commit -- background job saves progress or failure status
		frappe.db.commit()


def _should_refresh_total_monthly_sales():
	# "Each Transaction" updates on submit; refresh the cached figure for the
	# scheduled frequencies only ("Monthly" just on the 1st).
	frequency = frappe.get_single_value("Selling Settings", "sales_update_frequency")
	if frequency == "Monthly":
		return frappe.utils.now_datetime().day == 1
	return frequency == "Daily"


@frappe.whitelist()
def get_children(doctype: str, parent: str | None = None, company: str | None = None, is_root: bool = False):
	if parent is None or parent == "All Companies":
		parent = ""

	filters = {"parent_company": parent} if parent else {"parent_company": ["is", "not set"]}

	# get_list, not get_all: it applies the caller's Company permission and their Company User
	# Permissions, so a restricted user sees only their own companies. Matches the sibling tree
	# source in accounts/utils.py, which already uses get_list.
	return frappe.get_list(
		"Company",
		filters=filters,
		fields=["name as value", "is_group as expandable"],
	)


@frappe.whitelist(methods=["POST"])
def add_node():
	from frappe.desk.treeview import make_tree_args

	args = frappe.form_dict
	args = make_tree_args(**args)

	# This is the Company tree's "add node" action; `args` comes straight from form_dict, so without
	# this the caller chooses the doctype that gets created. insert() would still check permissions
	# on whatever they named, but nothing else here is meant to build anything but a Company.
	args.doctype = "Company"

	if args.parent_company == "All Companies":
		args.parent_company = None

	frappe.get_doc(args).insert()


def get_all_transactions_annual_history(company):
	out = {}

	one_year_ago = add_to_date(nowdate(), years=-1)
	date_doctypes = [
		("Quotation", "transaction_date"),
		("Sales Order", "transaction_date"),
		("Delivery Note", "posting_date"),
		("Sales Invoice", "posting_date"),
		("Issue", "creation"),
		("Project", "creation"),
	]

	from frappe.query_builder.functions import Count

	# Count per date in the DB (one grouped query per DocType) rather than streaming every
	# transaction row into Python. A portable UNION across these mixed date columns isn't
	# straightforward, so we aggregate each DocType and merge the per-date counts.
	counts = Counter()
	for doctype, date_field in date_doctypes:
		dt = frappe.qb.DocType(doctype)
		date_col = getattr(dt, date_field)
		rows = (
			frappe.qb.from_(dt)
			.select(date_col.as_("transaction_date"), Count("*").as_("count"))
			.where((dt.company == company) & (date_col > one_year_ago))
			.groupby(date_col)
			.run(as_dict=True)
		)
		for row in rows:
			counts[row.transaction_date] += row.count

	for transaction_date, count in counts.items():
		out.update({get_timestamp(transaction_date): count})

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
def get_default_company_address(
	name: str,
	sort_key: Literal["is_shipping_address", "is_primary_address"] = "is_primary_address",
	existing_address: str | None = None,
):
	# `Literal` is NOT enforced by typing_validations — measured, sort_key="name" was accepted — and
	# addr[sort_key] is a column reference, so check it here.
	if sort_key not in ("is_shipping_address", "is_primary_address"):
		frappe.throw(_("Invalid sort key"), frappe.PermissionError)

	# Same boundary as accounts/custom/address.py::get_shipping_address: `select` denies the portal
	# identities and costs none of the twelve transaction-writing roles, and the company scoping is
	# what actually closes the cross-company read.
	frappe.has_permission("Company", ptype="select", throw=True)

	from erpnext.stock.doctype.company_restriction.company_restriction import get_allowed_companies

	allowed_companies = get_allowed_companies(frappe.session.user, "Address")
	if allowed_companies and name not in allowed_companies:
		frappe.throw(_("Not permitted for {0}").format(name), frappe.PermissionError)

	addr = frappe.qb.DocType("Address")
	dl = frappe.qb.DocType("Dynamic Link")
	out = (
		frappe.qb.from_(addr)
		.inner_join(dl)
		.on(dl.parent == addr.name)
		.select(addr.name, addr[sort_key])
		.where(
			(dl.link_doctype == "Company")
			& (dl.link_name == name)
			& ((addr.disabled == 0) | addr.disabled.isnull())
		)
		.run()
	)

	if existing_address:
		if existing_address in [d[0] for d in out]:
			return existing_address

	if out:
		return max(out, key=lambda x: x[1])[0]  # find max by sort_key
	else:
		return None


@frappe.whitelist()
def get_billing_shipping_address(
	name: str, billing_address: str | None = None, shipping_address: str | None = None
):
	primary_address = get_default_company_address(name, "is_primary_address", billing_address)
	shipping_address = get_default_company_address(name, "is_shipping_address", shipping_address)

	return {"primary_address": primary_address, "shipping_address": shipping_address}


@frappe.whitelist(methods=["POST"])
def create_transaction_deletion_request(company: str):
	frappe.only_for("System Manager")
	# User Permission check
	frappe.has_permission("Company", ptype="delete", doc=company, throw=True)

	from erpnext.setup.doctype.transaction_deletion_record.transaction_deletion_record import (
		is_deletion_doc_running,
	)

	is_deletion_doc_running(company)

	tdr = frappe.get_doc({"doctype": "Transaction Deletion Record", "company": company})
	tdr.flags.ignore_permissions = 1
	tdr.insert()

	tdr.generate_to_delete_list()
	tdr.reload()

	tdr.submit()

	frappe.msgprint(
		_("Transaction Deletion Document {0} has been triggered for company {1}").format(
			get_link_to_form("Transaction Deletion Record", tdr.name), frappe.bold(company)
		)
	)
