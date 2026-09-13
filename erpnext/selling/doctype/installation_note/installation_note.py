# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.utils import cstr, escape_html, getdate

from erpnext.stock.serial_batch_bundle import get_serial_batch_list_from_item
from erpnext.stock.serial_batch_identity import SerialBatchIdentity
from erpnext.stock.utils import get_valid_serial_nos
from erpnext.utilities.transaction_base import TransactionBase


class InstallationNote(TransactionBase):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.selling.doctype.installation_note_item.installation_note_item import (
			InstallationNoteItem,
		)

		address_display: DF.TextEditor | None
		amended_from: DF.Link | None
		company: DF.Link
		contact_display: DF.SmallText | None
		contact_email: DF.Data | None
		contact_mobile: DF.SmallText | None
		contact_person: DF.Link | None
		customer: DF.Link
		customer_address: DF.Link | None
		customer_group: DF.Link | None
		customer_name: DF.Data | None
		inst_date: DF.Date
		inst_time: DF.Time | None
		items: DF.Table[InstallationNoteItem]
		naming_series: DF.Literal["MAT-INS-.YYYY.-"]
		project: DF.Link | None
		remarks: DF.SmallText | None
		status: DF.Literal["Draft", "Submitted", "Cancelled"]
		territory: DF.Link
	# end: auto-generated types

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.status_updater = [
			{
				"source_dt": "Installation Note Item",
				"target_dt": "Delivery Note Item",
				"target_field": "installed_qty",
				"target_ref_field": "qty",
				"join_field": "prevdoc_detail_docname",
				"target_parent_dt": "Delivery Note",
				"target_parent_field": "per_installed",
				"source_field": "qty",
				"percent_join_field": "prevdoc_docname",
				"status_field": "installation_status",
				"keyword": "Installed",
				"overflow_type": "installation",
			}
		]

	def validate(self):
		self.validate_installation_date()
		self.check_item_table()

		from erpnext.controllers.selling_controller import set_default_income_account_for_item

		set_default_income_account_for_item(self)

	def is_serial_no_added(self, item_code, serial_no):
		has_serial_no = frappe.db.get_value("Item", item_code, "has_serial_no")
		if has_serial_no == 1 and not serial_no:
			frappe.throw(_("Serial No is mandatory for Item {0}").format(item_code))
		elif has_serial_no != 1 and cstr(serial_no).strip():
			frappe.throw(_("Item {0} is not a serialized Item").format(item_code))

	def get_prevdoc_serial_no(self, prevdoc_detail_docname):
		row = frappe.db.get_value(
			"Delivery Note Item",
			prevdoc_detail_docname,
			["item_code", "serial_no", "serial_and_batch_bundle"],
			as_dict=True,
		)
		return get_serial_batch_list_from_item(row)[0] if row else []

	def is_serial_no_match(self, cur_s_no, prevdoc_s_no, prevdoc_docname):
		for sr in cur_s_no:
			if sr not in prevdoc_s_no:
				number = frappe.get_cached_value("Serial No", sr, "serial_no")
				frappe.throw(
					_("Serial No {0} does not belong to Delivery Note {1}").format(
						escape_html(number), escape_html(prevdoc_docname)
					)
				)

	def validate_serial_no(self):
		for d in self.get("items"):
			if (
				d.serial_and_batch_bundle
				and frappe.get_cached_value("Serial and Batch Bundle", d.serial_and_batch_bundle, "item_code")
				!= d.item_code
			):
				frappe.throw(
					_("Row #{0}: Serial and Batch Bundle does not belong to Item {1}").format(
						d.idx, escape_html(d.item_code)
					)
				)
			serial_ids = get_serial_batch_list_from_item(d)[0]
			numbers = SerialBatchIdentity("Serial No").get_numbers(d.item_code, serial_ids)
			serial_text = "\n".join(numbers)
			self.is_serial_no_added(d.item_code, serial_text)
			if serial_ids:
				get_valid_serial_nos(serial_text, d.qty, d.item_code)
				if d.prevdoc_detail_docname:
					self.is_serial_no_match(
						serial_ids, self.get_prevdoc_serial_no(d.prevdoc_detail_docname), d.prevdoc_docname
					)

	def validate_installation_date(self):
		for d in self.get("items"):
			if d.prevdoc_docname:
				d_date = frappe.db.get_value("Delivery Note", d.prevdoc_docname, "posting_date")
				if d_date > getdate(self.inst_date):
					frappe.throw(
						_("Installation date cannot be before delivery date for Item {0}").format(d.item_code)
					)

	def check_item_table(self):
		if not (self.get("items")):
			frappe.throw(_("Please pull items from Delivery Note"))

	def on_update(self):
		self.db_set("status", "Draft")

	def on_submit(self):
		self.validate_serial_no()
		self.update_prevdoc_status()
		self.db_set("status", "Submitted")

	def on_cancel(self):
		self.update_prevdoc_status()
		self.db_set("status", "Cancelled")
