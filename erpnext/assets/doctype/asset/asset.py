# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, get_link_to_form, flt

from assets.asset.doctype.asset_activity.asset_activity import create_asset_activity
from assets.asset.doctype.depreciation_schedule_.depreciation_schedule_ import create_depreciation_schedules
from erpnext.controllers.base_asset import BaseAsset, get_purchase_details


class Asset_(BaseAsset):
	def validate(self):
		super().validate()

		self.validate_purchase_document()
		self.validate_gross_purchase_amount()
		self.validate_item()
		self.validate_cost_center()

	def after_insert(self):
		if not self.is_serialized_asset and self.calculate_depreciation:
			# if this is moved to validate(), an error will be raised while
			# linking depr schedules to assets during the first save
			create_depreciation_schedules(self)

	def before_submit(self):
		super().before_submit()

		if self.is_serialized_asset:
			from assets.asset.doctype.asset_serial_no.asset_serial_no import create_asset_serial_no_docs

			create_asset_serial_no_docs(self)

	def validate_purchase_document(self):
		if self.is_existing_asset:
			if self.purchase_invoice:
				frappe.throw(_("Purchase Invoice cannot be made against an existing asset {0}")
					.format(self.name))

		else:
			purchase_doc = "Purchase Invoice" if self.purchase_invoice else "Purchase Receipt"
			purchase_docname = self.purchase_invoice or self.purchase_receipt
			purchase_doc = frappe.get_doc(purchase_doc, purchase_docname)

			if purchase_doc.get("company") != self.company:
				frappe.throw(_("Company of asset {0} and purchase document {1} doesn't match.")
					.format(self.name, purchase_doc.get("name")))

			if (is_cwip_accounting_enabled(self.asset_category)
				and not self.purchase_receipt
				and self.purchase_invoice
				and not frappe.db.get_value("Purchase Invoice", self.purchase_invoice, "update_stock")):
				frappe.throw(_("Update stock must be enable for the purchase invoice {0}")
					.format(self.purchase_invoice))

	def validate_item(self):
		item = frappe.get_cached_value("Item",
			self.item_code,
			["is_fixed_asset", "is_stock_item", "disabled"],
			as_dict=1)

		if not item:
			frappe.throw(_("Item {0} does not exist").format(self.item_code))
		elif item.disabled:
			frappe.throw(_("Item {0} has been disabled").format(self.item_code))
		elif not item.is_fixed_asset:
			frappe.throw(_("Item {0} must be a Fixed Asset Item").format(self.item_code))
		elif item.is_stock_item:
			frappe.throw(_("Item {0} must be a non-stock item").format(self.item_code))

	def validate_gross_purchase_amount(self):
		if not flt(self.gross_purchase_amount):
			frappe.throw(_("Gross Purchase Amount is mandatory"), frappe.MandatoryError)

		purchase_doctype, purchase_docname = get_purchase_details(self)

		if purchase_docname:
			base_net_rate, item_tax_amount = frappe.get_value(
				purchase_doctype + " Item",
				filters = {
					"parent": purchase_docname,
					"item_code": self.item_code
				},
				fields = ["base_net_rate", "item_tax_amount"]
			)

			if self.gross_purchase_amount != (base_net_rate + item_tax_amount):
				self.gross_purchase_amount = base_net_rate + item_tax_amount

	def validate_cost_center(self):
		if not self.cost_center:
			return

		cost_center_company = frappe.db.get_value("Cost Center", self.cost_center, "company")
		if cost_center_company != self.company:
			frappe.throw(
				_("Selected Cost Center {} doesn't belongs to {}").format(
					frappe.bold(self.cost_center), frappe.bold(self.company)
				),
				title=_("Invalid Cost Center"),
			)

def is_cwip_accounting_enabled(asset_category):
	return cint(frappe.db.get_value("Asset Category", asset_category, "enable_cwip_accounting"))

@frappe.whitelist()
def split_asset(asset, num_of_assets_to_be_separated):
	if isinstance(asset, str):
		asset = frappe.get_doc("Asset", asset)

	if isinstance(num_of_assets_to_be_separated, str):
		num_of_assets_to_be_separated = int(num_of_assets_to_be_separated)

	validate_num_of_assets_to_be_separated(asset, num_of_assets_to_be_separated)

	new_asset = create_new_asset(asset, num_of_assets_to_be_separated)

	if new_asset.calculate_depreciation:
		submit_copies_of_depreciation_schedules(new_asset.name, asset.name)

	update_existing_asset(asset, num_of_assets_to_be_separated)

	record_asset_split(asset, new_asset, num_of_assets_to_be_separated)
	display_message_on_successfully_splitting_asset(asset, new_asset)

def validate_num_of_assets_to_be_separated(asset, num_of_assets_to_be_separated):
	if num_of_assets_to_be_separated >= asset.num_of_assets:
		frappe.throw(_("Number of Assets to be Separated should be less than the total Number of Assets, which is {0}.")
			.format(frappe.bold(asset.num_of_assets)), title=_("Invalid Number"))

def create_new_asset(asset, num_of_assets_to_be_separated):
	new_asset = frappe.copy_doc(asset)
	new_asset.num_of_assets = num_of_assets_to_be_separated
	new_asset.flags.split_asset = True
	new_asset.submit()
	new_asset.flags.split_asset = False

	return new_asset

def submit_copies_of_depreciation_schedules(new_asset, original_asset):
	new_schedules = frappe.get_all(
		"Depreciation Schedule",
		filters = {
			"asset": new_asset
		},
		fields = ["name", "finance_book"]
	)

	map_to_original_schedules = get_map_to_original_schedules(original_asset, new_schedules)

	for schedule in new_schedules:
		ds = frappe.get_doc("Depreciation Schedule", schedule["name"])

		ds.notes = _("This is a copy of {0} created when Asset {1} was split to form Asset {2}.").format(
			get_link_to_form("Depreciation Schedule", map_to_original_schedules[ds.name]),
			get_link_to_form("Asset", original_asset),
			get_link_to_form("Asset", new_asset)
		)
		ds.submit()

def get_map_to_original_schedules(original_asset, new_schedules):
	"""
		Returns dictionary in the form {new_ds1: original_ds1, new_ds2: original_ds2...}
	"""
	original_schedules = frappe.get_all(
		"Depreciation Schedule",
		filters = {
			"asset": original_asset
		},
		fields = ["name", "finance_book"]
	)

	new_schedules_dict = turn_list_of_dicts_to_dicts(new_schedules)
	original_schedules_dict = turn_list_of_dicts_to_dicts(original_schedules)
	map_to_original_schedules = merge_dictionaries(new_schedules_dict, original_schedules_dict, new_schedules)

	return map_to_original_schedules

def turn_list_of_dicts_to_dicts(schedules):
	"""
		Converts [{"name": name1, "finance_book": fb1}, ...] into {fb1: name1, ...}
	"""
	schedules_dict = {}
	for schedule in schedules:
		schedules_dict.update({
			schedule["finance_book"]: schedule["name"]
		})

	return schedules_dict

def merge_dictionaries(new_schedules_dict, original_schedules_dict, new_schedules):
	"""
		Converts {fb1: name1, fb2: name2...} and {fb1: name3, fb2: name4...} into {name1: name3, name2: name4...}
	"""
	finance_books = get_finance_books(new_schedules)

	map_to_original_schedules = {}
	for finance_book in finance_books:
		map_to_original_schedules.update({
			new_schedules_dict[finance_book]: original_schedules_dict[finance_book]
		})

	return map_to_original_schedules

def get_finance_books(new_schedules):
	return [schedule["finance_book"] for schedule in new_schedules]

def update_existing_asset(asset, num_of_assets_to_be_separated):
	asset.flags.ignore_validate_update_after_submit = True
	asset.num_of_assets -= num_of_assets_to_be_separated
	asset.save()

def record_asset_split(asset, new_asset, num_of_assets_to_be_separated):
	split_assets = [asset.name, new_asset.name]
	is_plural = "s" if num_of_assets_to_be_separated > 1 else ""

	for split_asset in split_assets:
		create_asset_activity(
			asset = split_asset,
			activity_type = "Split",
			reference_doctype = asset.doctype,
			reference_docname = asset.name,
			notes = _("{0} asset{1} separated from {2} into {3}.")
				.format(num_of_assets_to_be_separated, is_plural, asset.name, new_asset.name)
		)

def display_message_on_successfully_splitting_asset(asset, new_asset):
	new_asset_link = frappe.bold(get_link_to_form("Asset", new_asset.name))
	message = _("Asset {0} split successfully. New Asset doc: {1}").format(asset.name, new_asset_link)

	frappe.msgprint(message, title="Sucess", indicator="green")
