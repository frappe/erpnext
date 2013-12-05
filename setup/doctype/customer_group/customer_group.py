# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import msgprint

	
from webnotes.utils.nestedset import DocTypeNestedSet
class DocType(DocTypeNestedSet):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.nsm_parent_field = 'parent_customer_group';

	def validate(self): 
		if webnotes.conn.sql("select name from `tabCustomer Group` where name = %s and docstatus = 2", 
		 		(self.doc.customer_group_name)):
			msgprint("""Another %s record is trashed. 
				To untrash please go to Setup -> Recycle Bin.""" % 
				(self.doc.customer_group_name), raise_exception = 1)		

	def on_update(self):
		self.validate_name_with_customer()
		super(DocType, self).on_update()
		self.validate_one_root()
		
	def validate_name_with_customer(self):
		if webnotes.conn.exists("Customer", self.doc.name):
			webnotes.msgprint("An Customer exists with same name (%s), \
				please change the Customer Group name or rename the Customer" % 
				self.doc.name, raise_exception=1)

	def on_trash(self):
		cust = webnotes.conn.sql("select name from `tabCustomer` where ifnull(customer_group, '') = %s", 
		 	self.doc.name)
		cust = [d[0] for d in cust]
		if cust:
			msgprint("""Customer Group: %s can not be trashed/deleted \
				because it is used in customer: %s. 
				To trash/delete this, remove/change customer group in customer master""" %
				(self.doc.name, cust or ''), raise_exception=1)

		if webnotes.conn.sql("select name from `tabCustomer Group` where parent_customer_group = %s \
				and docstatus != 2", self.doc.name):
			msgprint("Child customer group exists for this customer group. \
				You can not trash/cancel/delete this customer group.", raise_exception=1)

		# rebuild tree
		super(DocType, self).on_trash()
