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

	def before_save(self):
		if not self.on_hold:
			self.hold_type = ''
			self.release_date = ''
		elif self.on_hold and not self.hold_type:
			self.hold_type = 'All'

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
		# validation for Naming Series mandatory field...
		if frappe.defaults.get_global_default('supp_master_name') == 'Naming Series':
			if not self.naming_series:
				msgprint(_("Series is mandatory"), raise_exception=1)

		validate_party_accounts(self)
		self.validate_internal_supplier()

	def validate_internal_supplier(self):
		internal_supplier = frappe.db.get_value("Supplier",
			{"is_internal_supplier": 1, "represents_company": self.represents_company, "name": ("!=", self.name)}, "name")

		if internal_supplier:
			frappe.throw(_("Internal Supplier for company {0} already exists").format(
				frappe.bold(self.represents_company)))

	def on_trash(self):
		delete_contact_and_address('Supplier', self.name)

	def after_rename(self, olddn, newdn, merge=False):
		if frappe.defaults.get_global_default('supp_master_name') == 'Supplier Name':
			frappe.db.set(self, "supplier_name", newdn)

	def create_onboarding_docs(self, args):
		company = frappe.defaults.get_defaults().get('company') or \
			frappe.db.get_single_value('Global Defaults', 'default_company')

		for i in range(1, args.get('max_count')):
			supplier = args.get('supplier_name_' + str(i))
			if supplier:
				try:
					doc = frappe.get_doc({
						'doctype': self.doctype,
						'supplier_name': supplier,
						'supplier_group': _('Local'),
						'company': company
					}).insert()

					if args.get('supplier_email_' + str(i)):
						from erpnext.selling.doctype.customer.customer import create_contact
						create_contact(supplier, 'Supplier',
							doc.name, args.get('supplier_email_' + str(i)))
				except frappe.NameError:
					pass