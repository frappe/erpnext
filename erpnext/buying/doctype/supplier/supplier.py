# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.defaults
from frappe import msgprint, _
from frappe.model.naming import make_autoname
from frappe.geo.address_and_contact import (load_address_and_contact,
	delete_contact_and_address)

from erpnext.utilities.transaction_base import TransactionBase
from erpnext.accounts.party import validate_party_accounts, get_timeline_data # keep this

class Supplier(TransactionBase):
	def get_feed(self):
		return self.supplier_name

	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self, "supplier")
		self.load_dashboard_info()

	def load_dashboard_info(self):
		billing_this_year = frappe.db.sql("""
			select sum(credit_in_account_currency) - sum(debit_in_account_currency)
			from `tabGL Entry`
			where voucher_type='Purchase Invoice' and party_type = 'Supplier'
				and party=%s and fiscal_year = %s""",
			(self.name, frappe.db.get_default("fiscal_year")))

		total_unpaid = frappe.db.sql("""select sum(outstanding_amount)
			from `tabPurchase Invoice`
			where supplier=%s and docstatus = 1""", self.name)


		info = {}
		info["billing_this_year"] = billing_this_year[0][0] if billing_this_year else 0
		info["total_unpaid"] = total_unpaid[0][0] if total_unpaid else 0

		self.set_onload('dashboard_info', info)

	def autoname(self):
		supp_master_name = frappe.defaults.get_global_default('supp_master_name')
		if supp_master_name == 'Supplier Name':
			self.name = self.supplier_name
		else:
			self.name = make_autoname(self.naming_series + '.#####')

	def on_update(self):
		if not self.naming_series:
			self.naming_series = ''

	def validate(self):
		#validation for Naming Series mandatory field...
		if frappe.defaults.get_global_default('supp_master_name') == 'Naming Series':
			if not self.naming_series:
				msgprint(_("Series is mandatory"), raise_exception=1)

		validate_party_accounts(self)

	def on_trash(self):
		delete_contact_and_address('Supplier', self.name)

	def after_rename(self, olddn, newdn, merge=False):
		if frappe.defaults.get_global_default('supp_master_name') == 'Supplier Name':
			frappe.db.set(self, "supplier_name", newdn)
