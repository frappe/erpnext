# Copyright (c) 2016, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_link_to_form

from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import get_dimensions
from erpnext.assets.doctype.asset.depreciation import (
	get_depreciation_accounts,
	get_disposal_account_and_cost_center,
)
from erpnext.assets.doctype.asset_activity.asset_activity import add_asset_activity
from erpnext.assets.doctype.asset_depreciation_schedule.asset_depreciation_schedule import (
	get_asset_depr_schedule_doc,
	get_depr_schedule,
)


@frappe.whitelist()
def make_sales_invoice(asset: str, item_code: str, company: str, sell_qty: int, serial_no: str | None = None):
	asset_doc = frappe.get_doc("Asset", asset)
	si = frappe.new_doc("Sales Invoice")
	si.company = company
	si.currency = frappe.get_cached_value("Company", company, "default_currency")
	disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(company)
	si.append(
		"items",
		{
			"item_code": item_code,
			"is_fixed_asset": 1,
			"asset": asset,
			"income_account": disposal_account,
			"serial_no": serial_no,
			"cost_center": depreciation_cost_center,
			"qty": sell_qty,
		},
	)

	accounting_dimensions = get_dimensions(with_cost_center_and_project=True)
	for dimension in accounting_dimensions[0]:
		si.update(
			{
				dimension["fieldname"]: asset_doc.get(dimension["fieldname"])
				or dimension.get("default_dimension")
			}
		)

	si.set_missing_values()
	return si


@frappe.whitelist()
def create_asset_maintenance(
	asset: str,
	item_code: str,
	item_name: str,
	asset_category: str,
	company: str,
):
	asset_maintenance = frappe.new_doc("Asset Maintenance")
	asset_maintenance.update(
		{
			"asset_name": asset,
			"company": company,
			"item_code": item_code,
			"item_name": item_name,
			"asset_category": asset_category,
		}
	)
	return asset_maintenance


@frappe.whitelist()
def create_asset_repair(
	company: str,
	asset: str,
	asset_name: str,
):
	asset_repair = frappe.new_doc("Asset Repair")
	asset_repair.update({"company": company, "asset": asset, "asset_name": asset_name})
	return asset_repair


@frappe.whitelist()
def create_asset_capitalization(
	company: str,
	asset: str,
	asset_name: str,
	item_code: str,
):
	asset_capitalization = frappe.new_doc("Asset Capitalization")
	asset_capitalization.update(
		{
			"target_asset": asset,
			"company": company,
			"target_asset_name": asset_name,
			"target_item_code": item_code,
		}
	)
	return asset_capitalization


@frappe.whitelist()
def create_asset_value_adjustment(
	asset: str,
	asset_category: str,
	company: str,
):
	asset_value_adjustment = frappe.new_doc("Asset Value Adjustment")
	asset_value_adjustment.update({"asset": asset, "company": company, "asset_category": asset_category})
	return asset_value_adjustment


@frappe.whitelist()
def make_journal_entry(asset_name: str):
	asset = frappe.get_doc("Asset", asset_name)
	(
		fixed_asset_account,
		accumulated_depreciation_account,
		depreciation_expense_account,
	) = get_depreciation_accounts(asset.asset_category, asset.company)

	depreciation_cost_center, depreciation_series = frappe.get_cached_value(
		"Company", asset.company, ["depreciation_cost_center", "series_for_depreciation_entry"]
	)
	depreciation_cost_center = asset.cost_center or depreciation_cost_center

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Depreciation Entry"
	je.naming_series = depreciation_series
	je.company = asset.company
	je.remark = _("Depreciation Entry against asset {0}").format(asset_name)

	je.append(
		"accounts",
		{
			"account": depreciation_expense_account,
			"reference_type": "Asset",
			"reference_name": asset.name,
			"cost_center": depreciation_cost_center,
		},
	)

	je.append(
		"accounts",
		{
			"account": accumulated_depreciation_account,
			"reference_type": "Asset",
			"reference_name": asset.name,
		},
	)

	return je


@frappe.whitelist()
def make_asset_movement(
	assets: list[dict] | str,
	purpose: str = "Transfer",
):
	if isinstance(assets, str):
		assets = json.loads(assets)

	if len(assets) == 0:
		frappe.throw(_("At least one asset has to be selected."))

	asset_movement = frappe.new_doc("Asset Movement")
	asset_movement.purpose = purpose
	for asset in assets:
		asset = frappe.get_doc("Asset", asset.get("name"))
		asset_movement.company = asset.get("company")
		asset_movement.append(
			"assets",
			{
				"asset": asset.get("name"),
				"source_location": asset.get("location"),
				"from_employee": asset.get("custodian"),
			},
		)

	if asset_movement.get("assets"):
		return asset_movement.as_dict()


@frappe.whitelist()
def split_asset(asset_name: str, split_qty: int):
	"""Split an asset into two based on the given quantity."""
	existing_asset = frappe.get_doc("Asset", asset_name)
	split_qty = cint(split_qty)

	validate_split_quantity(existing_asset, split_qty)
	remaining_qty = existing_asset.asset_quantity - split_qty

	splitted_asset = create_new_asset_from_split(existing_asset, split_qty)
	update_existing_asset_after_split(existing_asset, remaining_qty, splitted_asset)

	return splitted_asset


def validate_split_quantity(existing_asset, split_qty):
	if split_qty >= existing_asset.asset_quantity:
		frappe.throw(_("Split Quantity must be less than Asset Quantity"))


def create_new_asset_from_split(existing_asset, split_qty):
	"""Create a new asset from the split quantity."""
	return process_asset_split(existing_asset, split_qty, is_new_asset=True)


def update_existing_asset_after_split(existing_asset, remaining_qty, splitted_asset):
	"""Update the existing asset with the remaining quantity."""
	process_asset_split(existing_asset, remaining_qty, splitted_asset=splitted_asset)


def process_asset_split(existing_asset, split_qty, splitted_asset=None, is_new_asset=False):
	"""Handle asset creation or update during the split."""
	scaling_factor = flt(split_qty) / flt(existing_asset.asset_quantity)
	new_asset = frappe.copy_doc(existing_asset) if is_new_asset else splitted_asset
	asset_doc = new_asset if is_new_asset else existing_asset
	asset_doc.flags.is_split_asset = True

	set_split_asset_values(asset_doc, scaling_factor, split_qty, existing_asset, is_new_asset)
	log_asset_activity(existing_asset, asset_doc, splitted_asset, is_new_asset)

	update_finance_books(asset_doc, existing_asset, new_asset, scaling_factor, is_new_asset)
	return new_asset


def set_split_asset_values(asset_doc, scaling_factor, split_qty, existing_asset, is_new_asset):
	asset_doc.net_purchase_amount = existing_asset.net_purchase_amount * scaling_factor
	asset_doc.purchase_amount = existing_asset.net_purchase_amount * scaling_factor
	asset_doc.additional_asset_cost = existing_asset.additional_asset_cost * scaling_factor
	asset_doc.total_asset_cost = asset_doc.net_purchase_amount + asset_doc.additional_asset_cost
	asset_doc.opening_accumulated_depreciation = (
		existing_asset.opening_accumulated_depreciation * scaling_factor
	)
	asset_doc.value_after_depreciation = existing_asset.value_after_depreciation * scaling_factor
	asset_doc.asset_quantity = split_qty
	asset_doc.split_from = existing_asset.name if is_new_asset else None

	for row in asset_doc.get("finance_books"):
		row.value_after_depreciation = row.value_after_depreciation * scaling_factor
		row.expected_value_after_useful_life = row.expected_value_after_useful_life * scaling_factor

	if not is_new_asset:
		asset_doc.flags.ignore_validate_update_after_submit = True
		asset_doc.save()


def log_asset_activity(existing_asset, asset_doc, splitted_asset, is_new_asset):
	if is_new_asset:
		asset_doc.insert()
		add_asset_activity(
			asset_doc.name,
			_("Asset created after being split from Asset {0}").format(
				get_link_to_form("Asset", existing_asset.name)
			),
		)
		asset_doc.submit()
		asset_doc.set_status()
	else:
		add_asset_activity(
			existing_asset.name,
			_("Asset updated after being split into Asset {0}").format(
				get_link_to_form("Asset", splitted_asset.name)
			),
		)


def update_finance_books(asset_doc, existing_asset, new_asset, scaling_factor, is_new_asset):
	"""Update finance books and depreciation schedules for the asset."""
	for fb_row in asset_doc.get("finance_books"):
		reschedule_depr_for_updated_asset(existing_asset, new_asset, fb_row, scaling_factor, is_new_asset)

	if is_new_asset:
		for row in new_asset.get("finance_books"):
			depr_schedule_doc = get_depr_schedule(new_asset.name, "Active", row.finance_book)
			for schedule in depr_schedule_doc:
				if schedule.journal_entry:
					add_reference_in_jv_on_split(
						schedule.journal_entry,
						new_asset.name,
						existing_asset.name,
						schedule.depreciation_amount,
					)


def reschedule_depr_for_updated_asset(existing_asset, new_asset, fb_row, scaling_factor, is_new_asset):
	"""Reschedule depreciation for an asset after a split."""
	current_depr_schedule_doc = get_asset_depr_schedule_doc(
		existing_asset.name, "Active", fb_row.finance_book
	)
	if not current_depr_schedule_doc:
		return

	new_depr_schedule_doc = create_new_depr_schedule(
		current_depr_schedule_doc, existing_asset, new_asset, is_new_asset, fb_row
	)

	update_depreciation_terms(new_depr_schedule_doc, scaling_factor)
	add_depr_schedule_notes(new_depr_schedule_doc, existing_asset, new_asset, is_new_asset)

	if not is_new_asset:
		current_depr_schedule_doc.flags.should_not_cancel_depreciation_entries = True
		current_depr_schedule_doc.cancel()

	new_depr_schedule_doc.submit()


def create_new_depr_schedule(current_depr_schedule_doc, existing_asset, new_asset, is_new_asset, fb_row):
	"""Create a new depreciation schedule based on the current one."""
	new_depr_schedule_doc = frappe.copy_doc(current_depr_schedule_doc)
	new_depr_schedule_doc.asset_doc = new_asset if is_new_asset else existing_asset
	new_depr_schedule_doc.fb_row = fb_row
	new_depr_schedule_doc.fetch_asset_details()
	return new_depr_schedule_doc


def update_depreciation_terms(new_depr_schedule_doc, scaling_factor):
	"""Update depreciation terms with scaled amounts."""
	accumulated_depreciation = 0
	for term in new_depr_schedule_doc.get("depreciation_schedule"):
		depreciation_amount = flt(
			term.depreciation_amount * scaling_factor, term.precision("depreciation_amount")
		)
		term.depreciation_amount = depreciation_amount
		accumulated_depreciation = flt(
			accumulated_depreciation + depreciation_amount, term.precision("depreciation_amount")
		)
		term.accumulated_depreciation_amount = accumulated_depreciation


def add_depr_schedule_notes(new_depr_schedule_doc, existing_asset, new_asset, is_new_asset):
	notes = _("This schedule was created when Asset {0} was {1} into new Asset {2}.").format(
		get_link_to_form(existing_asset.doctype, existing_asset.name),
		"split" if is_new_asset else "updated after being split",
		get_link_to_form(new_asset.doctype, new_asset.name),
	)
	new_depr_schedule_doc.notes = notes


def add_reference_in_jv_on_split(entry_name, new_asset_name, old_asset_name, depreciation_amount):
	"""Add a reference to a new asset in a journal entry after a split."""
	journal_entry = frappe.get_doc("Journal Entry", entry_name)
	entries_to_add = []

	adjust_existing_accounts(journal_entry, old_asset_name, depreciation_amount, entries_to_add)
	add_new_entries(journal_entry, entries_to_add, new_asset_name, depreciation_amount)

	journal_entry.flags.ignore_validate_update_after_submit = True
	journal_entry.save()

	journal_entry.docstatus = 2
	journal_entry.make_gl_entries(1)
	journal_entry.docstatus = 1
	journal_entry.make_gl_entries()


def adjust_existing_accounts(journal_entry, old_asset_name, depreciation_amount, entries_to_add):
	"""Adjust existing accounts and prepare new entries for the new asset."""
	for account in journal_entry.get("accounts"):
		if account.reference_name == old_asset_name:
			entries_to_add.append(frappe.copy_doc(account).as_dict())
			adjust_account_balance(account, depreciation_amount)


def adjust_account_balance(account, depreciation_amount):
	"""Adjust the balance of an account based on the depreciation amount."""
	if account.credit:
		account.credit -= depreciation_amount
		account.credit_in_account_currency -= account.exchange_rate * depreciation_amount
	elif account.debit:
		account.debit -= depreciation_amount
		account.debit_in_account_currency -= account.exchange_rate * depreciation_amount


def add_new_entries(journal_entry, entries_to_add, new_asset_name, depreciation_amount):
	"""Add new entries for the new asset to the journal entry."""
	idx = len(journal_entry.get("accounts")) + 1
	for entry in entries_to_add:
		entry.reference_name = new_asset_name
		if entry.credit:
			entry.credit = depreciation_amount
			entry.credit_in_account_currency = entry.exchange_rate * depreciation_amount
		elif entry.debit:
			entry.debit = depreciation_amount
			entry.debit_in_account_currency = entry.exchange_rate * depreciation_amount
		entry.idx = idx
		idx += 1
		journal_entry.append("accounts", entry)
