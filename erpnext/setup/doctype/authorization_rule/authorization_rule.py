# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import cint, cstr, flt, has_common
from frappe import msgprint

from frappe.model.document import Document

class AuthorizationRule(Document):


	def check_duplicate_entry(self):
		exists = frappe.db.sql("""select name, docstatus from `tabAuthorization Rule` 
			where transaction = %s and based_on = %s and system_user = %s 
			and system_role = %s and approving_user = %s and approving_role = %s 
			and to_emp =%s and to_designation=%s and name != %s""", 
			(self.transaction, self.based_on, cstr(self.system_user), 
				cstr(self.system_role), cstr(self.approving_user), 
				cstr(self.approving_role), cstr(self.to_emp), 
				cstr(self.to_designation), self.name))
		auth_exists = exists and exists[0][0] or ''
		if auth_exists:
			if cint(exists[0][1]) == 2:
				msgprint("""Duplicate Entry. Please untrash Authorization Rule : %s \
					from Recycle Bin""" % (auth_exists), raise_exception=1)
			else:
				msgprint("Duplicate Entry. Please check Authorization Rule : %s" % 
					(auth_exists), raise_exception=1)


	def validate_master_name(self):
		if self.based_on == 'Customerwise Discount' and \
				not frappe.db.sql("""select name from tabCustomer 
					where name = %s and docstatus != 2""", (self.master_name)):
			msgprint("Please select valid Customer Name for Customerwise Discount", 
			 	raise_exception=1)
		elif self.based_on == 'Itemwise Discount' and \
				not frappe.db.sql("select name from tabItem where name = %s and docstatus != 2", 
				 	(self.master_name)):
			msgprint("Please select valid Item Name for Itemwise Discount", raise_exception=1)
		elif (self.based_on == 'Grand Total' or \
				self.based_on == 'Average Discount') and self.master_name:
			msgprint("Please remove Customer/Item Name for %s." % 
				self.based_on, raise_exception=1)


	def validate_rule(self):
		if self.transaction != 'Appraisal':
			if not self.approving_role and not self.approving_user:
				msgprint("Please enter Approving Role or Approving User", raise_exception=1)
			elif self.system_user and self.system_user == self.approving_user:
				msgprint("Approving User cannot be same as user the rule is Applicable To (User)", 
					raise_exception=1)
			elif self.system_role and self.system_role == self.approving_role:
				msgprint("Approving Role cannot be same as user the rule is \
					Applicable To (Role).", raise_exception=1)
			elif self.system_user and self.approving_role and \
			 		has_common([self.approving_role], [x[0] for x in \
					frappe.db.sql("select role from `tabUserRole` where parent = %s", \
					 	(self.system_user))]):
				msgprint("System User : %s is assigned role : %s. So rule does not make sense" % 
				 	(self.system_user,self.approving_role), raise_exception=1)
			elif self.transaction in ['Purchase Order', 'Purchase Receipt', \
					'Purchase Invoice', 'Stock Entry'] and self.based_on \
					in ['Average Discount', 'Customerwise Discount', 'Itemwise Discount']:
				msgprint("You cannot set authorization on basis of Discount for %s" % 
				 	self.transaction, raise_exception=1)
			elif self.based_on == 'Average Discount' and flt(self.value) > 100.00:
				msgprint("Discount cannot given for more than 100%", raise_exception=1)
			elif self.based_on == 'Customerwise Discount' and not self.master_name:
				msgprint("Please enter Customer Name for 'Customerwise Discount'", 
				 	raise_exception=1)
		else:
			if self.transaction == 'Appraisal' and self.based_on != 'Not Applicable':
				msgprint("Based on should be 'Not Applicable' while setting authorization rule\
				 	for 'Appraisal'", raise_exception=1)



	def validate(self):
		self.check_duplicate_entry()
		self.validate_rule()
		self.validate_master_name()
		if not self.value: self.value = 0.0