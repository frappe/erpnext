# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from erpnext.controllers.base_asset import BaseAsset, get_finance_books


class AssetSerialNo(BaseAsset):
	def validate(self):
		self.validate_asset()
		super().validate()

	def before_submit(self):
		self.validate_location()
		super().before_submit()

	def validate_asset(self):
		is_serialized_asset = frappe.db.get_value("Asset", self.asset, "is_serialized_asset")

		if not is_serialized_asset:
			frappe.throw(
				_("{0} is not a Serialized Asset").format(frappe.bold(self.asset)), title=_("Invalid Asset")
			)

	def validate_location(self):
		if not self.location:
			frappe.throw(_("Please enter Location"), title=_("Missing Field"))


@frappe.whitelist()
def create_asset_serial_no_docs(asset, num_of_assets=None):
	asset, finance_books, asset_value = get_asset_values(asset)
	start, total_num_of_assets = get_iteration_limits(asset, num_of_assets)

	created_serial_nos = []
	for i in range(start, total_num_of_assets):
		serial_no = frappe.get_doc(
			{
				"doctype": "Asset Serial No",
				"asset": asset.name,
				"serial_no": get_serial_no(asset.name, i),
				"asset_value": asset_value,
				"finance_books": finance_books,
			}
		)
		serial_no.save(ignore_permissions=True)

		created_serial_nos.append(serial_no.name)

	update_asset(asset, total_num_of_assets)
	display_message_on_successful_creation(created_serial_nos)


def get_asset_values(asset):
	if isinstance(asset, str):
		asset = frappe.get_doc("Asset", asset)

	finance_books = []
	if asset.calculate_depreciation:
		finance_books = get_finance_books(asset.asset_category)

	asset_value = asset.get_initial_asset_value()

	return asset, finance_books, asset_value


def get_iteration_limits(asset, num_of_assets):
	if not num_of_assets:
		start = 0
		total_num_of_assets = asset.num_of_assets
	else:
		start = asset.num_of_assets
		total_num_of_assets = int(num_of_assets) + start

	return start, total_num_of_assets


def update_asset(asset, total_num_of_assets):
	if asset.num_of_assets != total_num_of_assets:
		asset.flags.ignore_validate_update_after_submit = True
		asset.num_of_assets = total_num_of_assets
		asset.save()


def display_message_on_successful_creation(created_serial_nos):
	num_of_serial_nos_created = len(created_serial_nos)

	if num_of_serial_nos_created > 5:
		message = _("{0} Asset Serial Nos created successfully.").format(
			frappe.bold(num_of_serial_nos_created)
		)
	else:
		serial_no_links = list(
			map(lambda d: frappe.utils.get_link_to_form("Asset Serial No", d), created_serial_nos)
		)
		serial_no_links = frappe.bold(",".join(serial_no_links))

		is_plural = "s" if num_of_serial_nos_created != 1 else ""
		message = _("Asset Serial No{0} {1} created successfully.").format(is_plural, serial_no_links)

	frappe.msgprint(message, title="Sucess", indicator="green")


def get_serial_no(asset_name, num_of_assets_created):
	return asset_name + "-" + str(num_of_assets_created + 1)
