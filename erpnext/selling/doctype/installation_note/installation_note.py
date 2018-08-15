# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import cstr, getdate

from frappe import _
from erpnext.stock.utils import get_valid_serial_nos

from erpnext.utilities.transaction_base import TransactionBase

class InstallationNote(TransactionBase):
	def __init__(self, *args, **kwargs):
		super(InstallationNote, self).__init__(*args, **kwargs)
		self.status_updater = [{
			'source_dt': 'Installation Note Item',
			'target_dt': 'Delivery Note Item',
			'target_field': 'installed_qty',
			'target_ref_field': 'qty',
			'join_field': 'prevdoc_detail_docname',
			'target_parent_dt': 'Delivery Note',
			'target_parent_field': 'per_installed',
			'source_field': 'qty',
			'percent_join_field': 'prevdoc_docname',
			'status_field': 'installation_status',
			'keyword': 'Installed',
			'overflow_type': 'installation'
		}]

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

	def is_serial_no_exist(self, item_code, serial_no):
		for x in serial_no:
			if not frappe.db.exists("Serial No", x):
				frappe.throw(_("Serial No {0} does not exist").format(x))

	def get_prevdoc_serial_no(self, prevdoc_detail_docname):
		serial_nos = frappe.db.get_value("Delivery Note Item",
			prevdoc_detail_docname, "serial_no")
		return get_valid_serial_nos(serial_nos)

	def is_serial_no_match(self, cur_s_no, prevdoc_s_no, prevdoc_docname):
		for sr in cur_s_no:
			if sr not in prevdoc_s_no:
				frappe.throw(_("Serial No {0} does not belong to Delivery Note {1}").format(sr, prevdoc_docname))

	def validate_serial_no(self):
		prevdoc_s_no, sr_list = [], []
		for d in self.get('items'):
			self.is_serial_no_added(d.item_code, d.serial_no)
			if d.serial_no:
				sr_list = get_valid_serial_nos(d.serial_no, d.qty, d.item_code)
				self.is_serial_no_exist(d.item_code, sr_list)

				prevdoc_s_no = self.get_prevdoc_serial_no(d.prevdoc_detail_docname)
				if prevdoc_s_no:
					self.is_serial_no_match(sr_list, prevdoc_s_no, d.prevdoc_docname)


	def validate_installation_date(self):
		for d in self.get('items'):
			if d.prevdoc_docname:
				d_date = frappe.db.get_value("Delivery Note", d.prevdoc_docname, "posting_date")
				if d_date > getdate(self.inst_date):
					frappe.throw(_("Installation date cannot be before delivery date for Item {0}").format(d.item_code))

	def check_item_table(self):
		if not(self.get('items')):
			frappe.throw(_("Please pull items from Delivery Note"))

	def on_update(self):
		frappe.db.set(self, 'status', 'Draft')

	def on_submit(self):
		self.validate_serial_no()
		self.update_prevdoc_status()
		frappe.db.set(self, 'status', 'Submitted')

	def on_cancel(self):
		self.update_prevdoc_status()
		frappe.db.set(self, 'status', 'Cancelled')
