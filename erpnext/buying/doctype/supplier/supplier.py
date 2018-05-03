# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import frappe.defaults
from frappe import msgprint, _
from frappe.model.naming import make_autoname
from frappe.contacts.address_and_contact import load_address_and_contact, delete_contact_and_address
from erpnext.utilities.transaction_base import TransactionBase
from erpnext.accounts.party import validate_party_accounts, get_dashboard_info

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

def get_timeline_data(doctype, name):
	'''returns timeline data based on linked records in dashboard'''
	from six import iteritems
	from frappe.utils import get_timestamp

	out = {}

	'''supplier quotation'''
	items = dict(frappe.db.sql('''select transaction_date, count(*)
		from `tabSupplier Quotation` where supplier=%s
			and transaction_date > date_sub(curdate(), interval 1 year)
			group by transaction_date''', name))

	for date, count in items.iteritems():
		timestamp = get_timestamp(date)
		out.update({ timestamp: count })

	'''purchase order'''
	items = dict(frappe.db.sql('''select transaction_date, count(*)
		from `tabPurchase Order` where supplier=%s
			and transaction_date > date_sub(curdate(), interval 1 year)
			group by transaction_date''', name))

	for date, count in iteritems(items):
		timestamp = get_timestamp(date)
		if not timestamp in out:
			out.update({timestamp: count})
		else :
			out.update({timestamp: out[timestamp] + count})

	'''purchase receipt'''
	items = dict(frappe.db.sql('''select posting_date, count(*)
		from `tabPurchase Receipt` where supplier=%s
			and posting_date > date_sub(curdate(), interval 1 year)
			group by posting_date''', name))

	for date, count in iteritems(items):
		timestamp = get_timestamp(date)
		if not timestamp in out:
			out.update({timestamp: count})
		else :
			out.update({timestamp: out[timestamp] + count})

	'''purchase invoice'''
	items = dict(frappe.db.sql('''select posting_date, count(*)
		from `tabPurchase Invoice` where supplier_name=%s
			and posting_date > date_sub(curdate(), interval 1 year)
			group by posting_date''', name))

	for date, count in iteritems(items):
		timestamp = get_timestamp(date)
		if not timestamp in out:
			out.update({timestamp: count})
		else :
			out.update({timestamp: out[timestamp] + count})

	'''request for quotation'''
	items = dict(frappe.db.sql('''select creation, count(*)
		from `tabRequest for Quotation Supplier` where supplier=%s
			and creation > date_sub(curdate(), interval 1 year)
			group by creation''', name))

	for date, count in iteritems(items):
		timestamp = get_timestamp(date)
		if not timestamp in out:
			out.update({timestamp: count})
		else :
			out.update({timestamp: out[timestamp] + count})

	return out