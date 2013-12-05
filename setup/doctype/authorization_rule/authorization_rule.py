# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cint, cstr, flt, has_common
from webnotes.model import db_exists
from webnotes.model.bean import copy_doclist
from webnotes import msgprint

	


class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl


	def check_duplicate_entry(self):
		exists = webnotes.conn.sql("""select name, docstatus from `tabAuthorization Rule` 
			where transaction = %s and based_on = %s and system_user = %s 
			and system_role = %s and approving_user = %s and approving_role = %s 
			and to_emp =%s and to_designation=%s and name != %s""", 
			(self.doc.transaction, self.doc.based_on, cstr(self.doc.system_user), 
				cstr(self.doc.system_role), cstr(self.doc.approving_user), 
				cstr(self.doc.approving_role), cstr(self.doc.to_emp), 
				cstr(self.doc.to_designation), self.doc.name))
		auth_exists = exists and exists[0][0] or ''
		if auth_exists:
			if cint(exists[0][1]) == 2:
				msgprint("""Duplicate Entry. Please untrash Authorization Rule : %s \
					from Recycle Bin""" % (auth_exists), raise_exception=1)
			else:
				msgprint("Duplicate Entry. Please check Authorization Rule : %s" % 
					(auth_exists), raise_exception=1)


	def validate_master_name(self):
		if self.doc.based_on == 'Customerwise Discount' and \
				not webnotes.conn.sql("select name from tabCustomer where name = '%s' and docstatus != 2" % \
				 	(self.doc.master_name)):
			msgprint("Please select valid Customer Name for Customerwise Discount", 
			 	raise_exception=1)
		elif self.doc.based_on == 'Itemwise Discount' and \
				not webnotes.conn.sql("select name from tabItem where name = '%s' and docstatus != 2" % \
				 	(self.doc.master_name)):
			msgprint("Please select valid Item Name for Itemwise Discount", raise_exception=1)
		elif (self.doc.based_on == 'Grand Total' or \
				self.doc.based_on == 'Average Discount') and self.doc.master_name:
			msgprint("Please remove Customer/Item Name for %s." % 
				self.doc.based_on, raise_exception=1)


	def validate_rule(self):
		if self.doc.transaction != 'Appraisal':
			if not self.doc.approving_role and not self.doc.approving_user:
				msgprint("Please enter Approving Role or Approving User", raise_exception=1)
			elif self.doc.system_user and self.doc.system_user == self.doc.approving_user:
				msgprint("Approving User cannot be same as user the rule is Applicable To (User)", 
					raise_exception=1)
			elif self.doc.system_role and self.doc.system_role == self.doc.approving_role:
				msgprint("Approving Role cannot be same as user the rule is \
					Applicable To (Role).", raise_exception=1)
			elif self.doc.system_user and self.doc.approving_role and \
			 		has_common([self.doc.approving_role], [x[0] for x in \
					webnotes.conn.sql("select role from `tabUserRole` where parent = '%s'" % \
					 	(self.doc.system_user))]):
				msgprint("System User : %s is assigned role : %s. So rule does not make sense" % 
				 	(self.doc.system_user,self.doc.approving_role), raise_exception=1)
			elif self.doc.transaction in ['Purchase Order', 'Purchase Receipt', \
					'Purchase Invoice', 'Stock Entry'] and self.doc.based_on \
					in ['Average Discount', 'Customerwise Discount', 'Itemwise Discount']:
				msgprint("You cannot set authorization on basis of Discount for %s" % 
				 	self.doc.transaction, raise_exception=1)
			elif self.doc.based_on == 'Average Discount' and flt(self.doc.value) > 100.00:
				msgprint("Discount cannot given for more than 100%", raise_exception=1)
			elif self.doc.based_on == 'Customerwise Discount' and not self.doc.master_name:
				msgprint("Please enter Customer Name for 'Customerwise Discount'", 
				 	raise_exception=1)
		else:
			if self.doc.transaction == 'Appraisal' and self.doc.based_on != 'Not Applicable':
				msgprint("Based on should be 'Not Applicable' while setting authorization rule\
				 	for 'Appraisal'", raise_exception=1)



	def validate(self):
		self.check_duplicate_entry()
		self.validate_rule()
		self.validate_master_name()
		if not self.doc.value: self.doc.value = 0.0