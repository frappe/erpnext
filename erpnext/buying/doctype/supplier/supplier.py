# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.defaults
from frappe import msgprint, _
from frappe.model.naming import set_name_by_naming_series
from frappe.contacts.address_and_contact import load_address_and_contact, delete_contact_and_address
from erpnext.utilities.transaction_base import TransactionBase
from erpnext.accounts.party import validate_party_accounts, get_dashboard_info, get_timeline_data # keep this

class Supplier(TransactionBase):
	def get_feed(self):
		return self.supplier_name

	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self)
		self.load_dashboard_info()

	def load_dashboard_info(self):
		info = get_dashboard_info(self.doctype, self.name)
		self.set_onload('dashboard_info', info)

	def autoname(self):
		supp_master_name = frappe.defaults.get_global_default('supp_master_name')
		if supp_master_name == 'Supplier Name':
			self.name = self.supplier_name
		else:
			set_name_by_naming_series(self)

	def on_update(self):
		if not self.naming_series:
			self.naming_series = ''

	def validate(self):
		#validation for Naming Series mandatory field...
		if frappe.defaults.get_global_default('supp_master_name') == 'Naming Series':
			if not self.naming_series:
				msgprint(_("Series is mandatory"), raise_exception=1)

		validate_party_accounts(self)
		self.validation_criteria()

	def on_trash(self):
		delete_contact_and_address('Supplier', self.name)

	def after_rename(self, olddn, newdn, merge=False):
		if frappe.defaults.get_global_default('supp_master_name') == 'Supplier Name':
			frappe.db.set(self, "supplier_name", newdn)

	def validation_criteria(self):
		validation_criteria = frappe.db.get_value("Buying Settings",None,"validation_criteria")
		name = self.name
		tax_id = self.tax_id
		pan_no = self.pan_no
		if validation_criteria == "Supplier ID + Tax ID + Pan No.":
			supplier_with_same_values = frappe.db.get_value("Supplier",filters={"name":name,"tax_id":tax_id,"pan_no":pan_no})
			if supplier_with_same_values:
				frappe.throw(_('Supplier with same Supplier ID ,Tax ID and Pan No. already exists'))
		elif validation_criteria == "Tax ID + Pan No.":
			supplier_with_same_values = frappe.db.get_value("Supplier",filters={"tax_id":tax_id,"pan_no":pan_no})
			if supplier_with_same_values:
				frappe.throw(_('Supplier with same Tax ID and Pan No. already exists'))
		elif validation_criteria == "Pan No.":
			supplier_with_same_values = frappe.db.get_value("Supplier",filters={"pan_no":pan_no})
			if supplier_with_same_values:
				frappe.throw(_('Supplier with same Pan No. already exists'))
		elif validation_criteria == "Tax ID":
			supplier_with_same_values = frappe.db.get_value("Supplier",filters={"tax_id":tax_id})
			if supplier_with_same_values:
				frappe.throw(_('Supplier with same Tax ID already exists'))
