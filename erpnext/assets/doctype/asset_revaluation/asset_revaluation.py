# Copyright (c) 2022, Ganga Manoj and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, formatdate, getdate

from erpnext.assets.doctype.asset_repair.asset_repair import (
	validate_num_of_assets,
	validate_serial_no,
)
from erpnext.assets.doctype.depreciation_schedule.depreciation_posting import (
	add_accounting_dimensions,
	get_depreciation_accounts,
	get_depreciation_details,
)


class AssetRevaluation(Document):
	def validate(self):
		self.validate_asset_values()
		self.set_current_asset_value()
		self.set_difference_amount()

	def on_submit(self):
		if self.current_asset_value > self.new_asset_value:
			self.make_depreciation_entry()
		else:
			self.prevent_increase_in_value()

	def validate_asset_values(self):
		purchase_date, is_serialized_asset, num_of_assets, is_depreciable_asset = frappe.db.get_value(
			"Asset",
			self.asset,
			["purchase_date", "is_serialized_asset", "num_of_assets", "calculate_depreciation"],
		)

		self.validate_transaction_date_against_purchase_date(purchase_date)

		if is_serialized_asset:
			validate_serial_no(self)
		else:
			validate_num_of_assets(self, num_of_assets)

		if not is_depreciable_asset:
			frappe.throw(_("Asset {} is not depreciable.").format(self.asset))

	def validate_transaction_date_against_purchase_date(self, purchase_date):
		if getdate(self.date) < getdate(purchase_date):
			frappe.throw(
				_("Asset Revaluation cannot be posted before Asset's purchase date: <b>{0}</b>.").format(
					formatdate(purchase_date)
				),
				title="Invalid Date",
			)

	def set_current_asset_value(self):
		if not self.current_asset_value and self.asset:
			self.current_asset_value = get_current_asset_value(
				self.asset, self.serial_no, self.finance_book
			)

	def set_difference_amount(self):
		self.difference_amount = abs(flt(self.current_asset_value - self.new_asset_value))

	def make_depreciation_entry(self):
		asset = frappe.get_doc("Asset", self.asset)

		credit_account, debit_account = get_depreciation_accounts(asset.asset_category, asset.company)
		depreciation_cost_center, _ = get_depreciation_details(asset)

		depr_entry = frappe.new_doc("Depreciation Entry")
		depr_entry.posting_date = self.date
		depr_entry.company = self.company
		depr_entry.asset = self.asset
		depr_entry.num_of_assest = self.num_of_assets
		depr_entry.serial_no = self.serial_no
		depr_entry.finance_book = self.finance_book
		depr_entry.credit_account = credit_account
		depr_entry.debit_account = debit_account
		depr_entry.depreciation_amount = self.difference_amount
		depr_entry.cost_center = depreciation_cost_center or self.cost_center
		depr_entry.reference_doctype = self.doctype
		depr_entry.reference_docname = self.name

		add_accounting_dimensions(depr_entry, asset)

		depr_entry.flags.ignore_permissions = True
		depr_entry.submit()

		self.db_set("depreciation_entry", depr_entry.name)

	def prevent_increase_in_value(self):
		frappe.throw(_("New Asset Value cannot be higher than Current Asset Value."))


@frappe.whitelist()
def get_current_asset_value(asset, serial_no=None, finance_book=None):
	if not finance_book:
		if serial_no:
			return frappe.db.get_value("Asset Serial No", serial_no, "asset_value")
		else:
			return frappe.db.get_value("Asset", asset, "asset_value")

	else:
		if serial_no:
			parent = serial_no
			parent_type = "Asset Serial No"
		else:
			parent = asset
			parent_type = "Asset"

		filters = {"parent": parent, "parenttype": parent_type, "finance_book": finance_book}

		return frappe.db.get_value("Asset Finance Book", filters, "asset_value")
