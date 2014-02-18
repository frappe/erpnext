# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.bean import getlist
from frappe.utils import flt
from frappe.utils.nestedset import DocTypeNestedSet

class DocType(DocTypeNestedSet):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.nsm_parent_field = 'parent_sales_person';

	def validate(self): 
		for d in getlist(self.doclist, 'target_details'):
			if not flt(d.target_qty) and not flt(d.target_amount):
				frappe.throw(_("Either target qty or target amount is mandatory."))
	
	def on_update(self):
		super(DocType, self).on_update()
		self.validate_one_root()
	
	def get_email_id(self):
		profile = frappe.conn.get_value("Employee", self.doc.employee, "user_id")
		if not profile:
			frappe.throw("User ID (Profile) not set for Employee %s" % self.doc.employee)
		else:
			return frappe.conn.get_value("Profile", profile, "email") or profile
		