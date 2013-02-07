# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes import msgprint

sql = webnotes.conn.sql
	
from webnotes.utils.nestedset import DocTypeNestedSet
class DocType(DocTypeNestedSet):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.nsm_parent_field = 'parent_customer_group';

	def validate(self): 
		if sql("select name from `tabCustomer Group` where name = %s and docstatus = 2", 
		 		(self.doc.customer_group_name)):
			msgprint("""Another %s record is trashed. 
				To untrash please go to Setup -> Recycle Bin.""" % 
				(self.doc.customer_group_name), raise_exception = 1)		

	def on_update(self):
		self.validate_name_with_customer()
		super(DocType, self).on_update()
		
	def validate_name_with_customer(self):
		if webnotes.conn.exists("Customer", self.doc.name):
			webnotes.msgprint("An Customer exists with same name (%s), \
				please change the Customer Group name or rename the Customer" % 
				self.doc.name, raise_exception=1)

	def on_trash(self):
		cust = sql("select name from `tabCustomer` where ifnull(customer_group, '') = %s", 
		 	self.doc.name)
		cust = [d[0] for d in cust]
		if cust:
			msgprint("""Customer Group: %s can not be trashed/deleted \
				because it is used in customer: %s. 
				To trash/delete this, remove/change customer group in customer master""" %
				(self.doc.name, cust or ''), raise_exception=1)

		if sql("select name from `tabCustomer Group` where parent_customer_group = %s \
				and docstatus != 2", self.doc.name):
			msgprint("Child customer group exists for this customer group. \
				You can not trash/cancel/delete this customer group.", raise_exception=1)

		# rebuild tree
		super(DocType, self).on_trash()

test_records = [
	[{
		"doctype": "Customer Group",
		"customer_group_name": "_Test Customer Group",
		"parent_customer_group": "All Customer Groups",
		"is_group": "No"
	}]
]