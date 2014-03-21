# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from frappe.utils import cint

class DocType:
	def __init__(self,doc,doclist):
		self.doc, self.doclist = doc,doclist

	def get_series(self):
		import frappe.model.doctype
		docfield = frappe.model.doctype.get('Sales Invoice')
		series = [d.options for d in docfield 
			if d.doctype == 'DocField' and d.fieldname == 'naming_series']
		return series and series[0] or ''

	def validate(self):
		self.check_for_duplicate()
		self.validate_expense_account()
		self.validate_all_link_fields()
		
	def check_for_duplicate(self):
		res = frappe.db.sql("""select name, user from `tabPOS Setting` 
			where ifnull(user, '') = %s and name != %s and company = %s""", 
			(self.doc.user, self.doc.name, self.doc.company))
		if res:
			if res[0][1]:
				msgprint("POS Setting '%s' already created for user: '%s' and company: '%s'" % 
					(res[0][0], res[0][1], self.doc.company), raise_exception=1)
			else:
				msgprint("Global POS Setting already created - %s for this company: '%s'" % 
					(res[0][0], self.doc.company), raise_exception=1)

	def validate_expense_account(self):
		if cint(frappe.defaults.get_global_default("auto_accounting_for_stock")) \
				and not self.doc.expense_account:
			msgprint(_("Expense Account is mandatory"), raise_exception=1)

	def validate_all_link_fields(self):
		accounts = {"Account": [self.doc.cash_bank_account, self.doc.income_account, 
			self.doc.expense_account], "Cost Center": [self.doc.cost_center], 
			"Warehouse": [self.doc.warehouse]}
		
		for link_dt, dn_list in accounts.items():
			for link_dn in dn_list:
				if link_dn and not frappe.db.exists({"doctype": link_dt, 
						"company": self.doc.company, "name": link_dn}):
					frappe.throw(link_dn +_(" does not belong to ") + self.doc.company)

	def on_update(self):
		self.set_defaults()

	def on_trash(self):
		self.set_defaults(include_current_pos=False)

	def set_defaults(self, include_current_pos=True):
		frappe.defaults.clear_default("is_pos")
		
		if not include_current_pos:
			condition = " where name != '%s'" % self.doc.name.replace("'", "\'")
		else:
			condition = ""

		pos_view_users = frappe.db.sql_list("""select user 
			from `tabPOS Setting` {0}""".format(condition))
		
		for user in pos_view_users:
			if user:
				frappe.defaults.set_user_default("is_pos", 1, user)
			else:
				frappe.defaults.set_global_default("is_pos", 1)