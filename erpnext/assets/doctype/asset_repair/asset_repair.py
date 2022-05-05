# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, get_link_to_form, getdate, time_diff_in_hours

from erpnext.accounts.general_ledger import make_gl_entries
from erpnext.assets.doctype.asset.asset import split_asset
from erpnext.controllers.accounts_controller import AccountsController
from erpnext.controllers.base_asset import get_asset_account


class AssetRepair(AccountsController):
	def validate(self):
		self.get_asset_doc()
		self.validate_asset()
		self.update_status()

		if self.get("stock_consumption"):
			self.validate_consumed_items()
			self.validate_warehouse()
			self.set_total_value()

		self.calculate_total_repair_cost()

	def before_submit(self):
		self.check_repair_status()
		self.split_asset_doc_if_required()

		if self.get("stock_consumption") or self.get("capitalize_repair_cost"):
			self.increase_asset_value()
		if self.get("stock_consumption"):
			self.decrease_stock_quantity()
		if self.get("capitalize_repair_cost"):
			self.make_gl_entries()

			if self.is_depreciable_asset() and self.get("increase_in_asset_life"):
				self.increase_asset_life()

		self.record_asset_repair()

	def before_cancel(self):
		self.get_asset_doc()

		if self.get("stock_consumption") or self.get("capitalize_repair_cost"):
			self.decrease_asset_value()
		if self.get("stock_consumption"):
			self.increase_stock_quantity()
		if self.get("capitalize_repair_cost"):
			self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry")
			self.make_gl_entries(cancel=True)

			if self.is_depreciable_asset() and self.get("increase_in_asset_life"):
				self.decrease_asset_life()

	def get_asset_doc(self):
		if self.get("serial_no"):
			self.asset_doc = frappe.get_doc("Asset Serial No", self.serial_no)
		else:
			self.asset_doc = frappe.get_doc("Asset", self.asset)

	def validate_asset(self):
		if self.asset_doc.doctype == "Asset":
			if self.asset_doc.is_serialized_asset:
				validate_serial_no(self)
			else:
				validate_num_of_assets(self, self.asset_doc.num_of_assets)

	def update_status(self):
		if self.repair_status == "Pending":
			frappe.db.set_value(self.asset_doc.doctype, self.asset_doc.name, "status", "Out of Order")
		else:
			self.asset_doc.set_status()

	def validate_consumed_items(self):
		if not self.items:
			frappe.throw(_("Please enter Consumed Items."), title=_("Missing Values"))

	def validate_warehouse(self):
		if not self.warehouse:
			frappe.throw(_("Please enter Warehouse."), title=_("Missing Value"))

	def set_total_value(self):
		for item in self.get("items"):
			item.amount = flt(item.rate) * flt(item.qty)

	def calculate_total_repair_cost(self):
		self.total_repair_cost = flt(self.repair_cost)

		total_value_of_stock_consumed = self.get_total_value_of_stock_consumed()
		self.total_repair_cost += total_value_of_stock_consumed

	def get_total_value_of_stock_consumed(self):
		total_value_of_stock_consumed = 0

		if self.get("stock_consumption"):
			for item in self.get("items"):
				total_value_of_stock_consumed += item.amount

		return total_value_of_stock_consumed

	def check_repair_status(self):
		if self.repair_status == "Pending":
			frappe.throw(_("Please update Repair Status."))

	def split_asset_doc_if_required(self):
		if self.asset_doc.doctype == "Asset" and not self.asset_doc.is_serialized_asset:
			if self.num_of_assets < self.asset_doc.num_of_assets:
				num_of_assets_to_be_separated = self.asset_doc.num_of_assets - self.num_of_assets

				split_asset(self.asset_doc, num_of_assets_to_be_separated)

	def increase_asset_value(self):
		total_value_of_stock_consumed = self.get_total_value_of_stock_consumed()
		increase_in_value = self.get_change_in_value(total_value_of_stock_consumed)

		if self.is_depreciable_asset():
			for row in self.asset_doc.finance_books:
				row.asset_value += increase_in_value

			self.asset_doc.update_asset_value()
		else:
			self.asset_doc.update_asset_value(increase_in_value)

		self.asset_doc.flags.ignore_validate_update_after_submit = True
		self.asset_doc.save()

	def decrease_asset_value(self):
		total_value_of_stock_consumed = self.get_total_value_of_stock_consumed()
		decrease_in_value = self.get_change_in_value(total_value_of_stock_consumed)

		if self.is_depreciable_asset():
			for row in self.asset_doc.finance_books:
				row.asset_value -= decrease_in_value

			self.asset_doc.update_asset_value()
		else:
			self.asset_doc.update_asset_value(-decrease_in_value)

		self.asset_doc.flags.ignore_validate_update_after_submit = True
		self.asset_doc.save()

	def get_change_in_value(self, total_value_of_stock_consumed):
		change_in_value = total_value_of_stock_consumed
		if self.capitalize_repair_cost:
			change_in_value += self.repair_cost

		return change_in_value

	def is_depreciable_asset(self):
		if self.asset_doc.doctype == "Asset":
			return self.asset_doc.calculate_depreciation
		else:
			return frappe.db.get_value("Asset", self.asset_doc.asset, "calculate_depreciation")

	def decrease_stock_quantity(self):
		stock_entry = frappe.get_doc(
			{"doctype": "Stock Entry", "stock_entry_type": "Material Issue", "company": self.company}
		)

		for item in self.get("items"):
			stock_entry.append(
				"items",
				{
					"s_warehouse": self.warehouse,
					"item_code": item.item_code,
					"qty": item.qty,
					"basic_rate": item.rate,
					"serial_no": item.serial_no,
				},
			)

		stock_entry.insert()
		stock_entry.submit()

		self.db_set("stock_entry", stock_entry.name)

	def increase_stock_quantity(self):
		stock_entry = frappe.get_doc("Stock Entry", self.stock_entry)
		stock_entry.flags.ignore_links = True
		stock_entry.cancel()

	def make_gl_entries(self, cancel=False):
		if flt(self.repair_cost) > 0:
			gl_entries = self.get_gl_entries()
			make_gl_entries(gl_entries, cancel)

	def get_gl_entries(self):
		gl_entries = []
		repair_and_maintenance_account = frappe.db.get_value(
			"Company", self.company, "repair_and_maintenance_account"
		)
		fixed_asset_account = get_asset_account(
			"fixed_asset_account", asset=self.asset, company=self.company
		)
		expense_account = (
			frappe.get_doc("Purchase Invoice", self.purchase_invoice).items[0].expense_account
		)

		gl_entries.append(
			self.get_gl_dict(
				{
					"account": expense_account,
					"credit": self.repair_cost,
					"credit_in_account_currency": self.repair_cost,
					"against": repair_and_maintenance_account,
					"voucher_type": self.doctype,
					"voucher_no": self.name,
					"cost_center": self.cost_center,
					"posting_date": getdate(),
					"company": self.company,
				},
				item=self,
			)
		)

		if self.get("stock_consumption"):
			# creating GL Entries for each row in Stock Items based on the Stock Entry created for it
			stock_entry = frappe.get_doc("Stock Entry", self.stock_entry)
			for item in stock_entry.items:
				gl_entries.append(
					self.get_gl_dict(
						{
							"account": item.expense_account,
							"credit": item.amount,
							"credit_in_account_currency": item.amount,
							"against": repair_and_maintenance_account,
							"voucher_type": self.doctype,
							"voucher_no": self.name,
							"cost_center": self.cost_center,
							"posting_date": getdate(),
							"company": self.company,
						},
						item=self,
					)
				)

		gl_entries.append(
			self.get_gl_dict(
				{
					"account": fixed_asset_account,
					"debit": self.total_repair_cost,
					"debit_in_account_currency": self.total_repair_cost,
					"against": expense_account,
					"voucher_type": self.doctype,
					"voucher_no": self.name,
					"cost_center": self.cost_center,
					"posting_date": getdate(),
					"against_voucher_type": "Purchase Invoice",
					"against_voucher": self.purchase_invoice,
					"company": self.company,
				},
				item=self,
			)
		)

		return gl_entries

	def increase_asset_life(self):
		self.asset_doc.flags.ignore_validate_update_after_submit = True
		self.asset_doc.enable_finance_books = self.has_enabled_finance_books()

		self.update_asset_life_in_asset_doc()
		self.asset_doc.create_schedules_if_depr_details_have_been_updated()
		self.asset_doc.submit_depreciation_schedules(
			notes=_(
				"This schedule was cancelled because {0} underwent a repair({1}) that extended its life."
			).format(
				get_link_to_form(self.asset_doc.doctype, self.asset_doc.name),
				get_link_to_form(self.doctype, self.name),
			)
		)
		self.asset_doc.save()

	def update_asset_life_in_asset_doc(self):
		if self.asset_doc.enable_finance_books:
			for row in self.asset_doc.finance_books:
				row.asset_life_in_months += self.increase_in_asset_life
		else:
			self.asset_doc.asset_life_in_months += self.increase_in_asset_life

	def decrease_asset_life(self):
		self.asset_doc.flags.ignore_validate_update_after_submit = True
		self.asset_doc.enable_finance_books = self.has_enabled_finance_books()

		self.reset_asset_life_in_asset_doc()
		self.asset_doc.create_schedules_if_depr_details_have_been_updated()
		self.asset_doc.submit_depreciation_schedules(
			notes=_(
				"This schedule was cancelled because the repair that extended {0}'s life({1}) was cancelled."
			).format(
				get_link_to_form(self.asset_doc.doctype, self.asset_doc.name),
				get_link_to_form(self.doctype, self.name),
			)
		)
		self.asset_doc.save()

	def reset_asset_life_in_asset_doc(self):
		if self.asset_doc.enable_finance_books:
			for row in self.asset_doc.finance_books:
				row.asset_life_in_months -= self.increase_in_asset_life
		else:
			self.asset_doc.asset_life_in_months -= self.increase_in_asset_life

	def has_enabled_finance_books(self):
		return frappe.db.get_single_value("Accounts Settings", "enable_finance_books")

	def record_asset_repair(self):
		from erpnext.assets.doctype.asset_activity.asset_activity import create_asset_activity
		from erpnext.assets.doctype.depreciation_schedule.depreciation_schedule import (
			get_asset_and_serial_no,
		)

		asset, serial_no = get_asset_and_serial_no(self.asset_doc)

		create_asset_activity(
			asset=asset,
			asset_serial_no=serial_no,
			activity_type="Repair",
			activity_date=self.completion_date,
			reference_doctype=self.doctype,
			reference_docname=self.name,
		)


@frappe.whitelist()
def get_downtime(failure_date, completion_date):
	downtime = time_diff_in_hours(completion_date, failure_date)
	return round(downtime, 2)


def validate_serial_no(doc):
	if not doc.serial_no:
		frappe.throw(
			_("Please enter Serial No as {0} is a Serialized Asset").format(frappe.bold(doc.asset)),
			title=_("Missing Serial No"),
		)


def validate_num_of_assets(doc, num_of_assets):
	if doc.num_of_assets > num_of_assets:
		frappe.throw(
			_("Number of Assets cannot be greater than {0}").format(frappe.bold(num_of_assets)),
			title=_("Number Exceeded Limit"),
		)

	if doc.num_of_assets < 1:
		frappe.throw(
			_("Number of Assets needs to be between <b>1</b> and {0}").format(frappe.bold(num_of_assets)),
			title=_("Invalid Number"),
		)
