# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.defaults
from frappe import msgprint, _
from frappe.model.naming import make_autoname
from erpnext.utilities.address_and_contact import load_address_and_contact
from erpnext.utilities.transaction_base import TransactionBase
from erpnext.accounts.party import validate_party_accounts, get_timeline_data # keep this
from erpnext.accounts.party_status import get_party_status

class Supplier(TransactionBase):
	def get_feed(self):
		return self.supplier_name

	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self, "supplier")

	def autoname(self):
		supp_master_name = frappe.defaults.get_global_default('supp_master_name')
		if supp_master_name == 'Supplier Name':
			self.name = self.supplier_name
		else:
			self.name = make_autoname(self.naming_series + '.#####')

	def update_address(self):
		frappe.db.sql("""update `tabAddress` set supplier_name=%s, modified=NOW()
			where supplier=%s""", (self.supplier_name, self.name))

	def update_contact(self):
		frappe.db.sql("""update `tabContact` set supplier_name=%s, modified=NOW()
			where supplier=%s""", (self.supplier_name, self.name))

	def on_update(self):
		if not self.naming_series:
			self.naming_series = ''

		self.update_address()
		self.update_contact()

	def validate(self):
		#validation for Naming Series mandatory field...
		if frappe.defaults.get_global_default('supp_master_name') == 'Naming Series':
			if not self.naming_series:
				msgprint(_("Series is mandatory"), raise_exception=1)

		validate_party_accounts(self)
		self.status = get_party_status(self)

	def get_contacts(self,nm):
		if nm:
			contact_details =frappe.db.convert_to_lists(frappe.db.sql("select name, CONCAT(IFNULL(first_name,''),' ',IFNULL(last_name,'')),contact_no,email_id from `tabContact` where supplier = %s", nm))

			return contact_details
		else:
			return ''

	def delete_supplier_address(self):
		for rec in frappe.db.sql("select * from `tabAddress` where supplier=%s", (self.name,), as_dict=1):
			frappe.db.sql("delete from `tabAddress` where name=%s",(rec['name']))

	def delete_supplier_contact(self):
		for contact in frappe.db.sql_list("""select name from `tabContact`
			where supplier=%s""", self.name):
				frappe.delete_doc("Contact", contact)

	def on_trash(self):
		self.delete_supplier_address()
		self.delete_supplier_contact()

	def after_rename(self, olddn, newdn, merge=False):
		set_field = ''
		if frappe.defaults.get_global_default('supp_master_name') == 'Supplier Name':
			frappe.db.set(self, "supplier_name", newdn)
			self.update_contact()
			set_field = ", supplier_name=%(newdn)s"
		self.update_supplier_address(newdn, set_field)

	def update_supplier_address(self, newdn, set_field):
		frappe.db.sql("""update `tabAddress` set address_title=%(newdn)s
			{set_field} where supplier=%(newdn)s"""\
			.format(set_field=set_field), ({"newdn": newdn}))