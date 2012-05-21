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

# Please edit this list and import only required elements
import webnotes

from webnotes.model.doc import Document
from webnotes.model.doclist import getlist
from webnotes.model.code import get_obj
from webnotes import session, form, is_testing, msgprint, errprint
from webnotes.utils import flt, cstr

sql = webnotes.conn.sql
convert_to_lists = webnotes.conn.convert_to_lists
	
# -----------------------------------------------------------------------------------------

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.nsm_parent_field = 'parent_sales_person';
	
	def check_state(self):
		return "\n" + "\n".join([i[0] for i in sql("select state_name from `tabState` where `tabState`.country='%s' " % self.doc.country)])


	# update Node Set Model
	def update_nsm_model(self):
		import webnotes
		import webnotes.utils.nestedset
		webnotes.utils.nestedset.update_nsm(self)

	# ON UPDATE
	#--------------------------------------
	def on_update(self):
		# update nsm
		self.update_nsm_model()	 


	def validate(self): 
		for d in getlist(self.doclist, 'target_details'):
			if not flt(d.target_qty) and not flt(d.target_amount):
				msgprint("Either target qty or target amount is mandatory.")
				raise Exception
				
		#self.sync_with_contact()
		
	def sync_with_contact(self):
		cid = sql("select name from tabContact where sales_person_id = %s and is_sales_person=1", self.doc.name)
		if cid:
			d = Document('Contact', cid[0][0])
		else:
			d = Document('Contact')
		
		name_split = self.doc.sales_person_name.split()
		d.contact_name = self.doc.sales_person_name
		d.first_name = name_split[0]
		d.last_name = len(name_split) > 1 and name_split[1] or ''
		d.email_id = self.doc.email_id
		d.contact_no = d.mobile_no = self.doc.mobile_no
		d.designation = self.doc.designation
		d.department = self.doc.department
		d.sales_person_id = self.doc.name
		d.is_sales_person = 1
		
		d.save(new = (not d.name))
		

	def on_trash(self):
		st = sql("select parent, parenttype from `tabSales Team` where ifnull(sales_person, '') = %s and docstatus != 2", self.doc.name)
		st = [(d[1] + ' : ' + d[0]) for d in st]
		if st:
			msgprint("""Sales Person: %s can not be trashed/deleted because it is used in  %s. 
				To trash/delete this, remove/change sales person in %s""" % (self.doc.name, st or '', st or ''), raise_exception=1)

		if sql("select name from `tabSales Person` where parent_sales_person = %s and docstatus != 2", self.doc.name):
			msgprint("Child sales person exists for this sales person. You can not trash/cancel this sales person.", raise_exception=1)

		# rebuild tree
		webnotes.conn.set(self.doc,'old_parent', '')
		self.update_nsm_model()
