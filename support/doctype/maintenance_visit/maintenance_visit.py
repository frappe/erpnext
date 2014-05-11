# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.utils import cstr
from webnotes.model.bean import getlist
from webnotes import msgprint

	

from utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
	
	def get_item_details(self, item_code):
		item = webnotes.conn.sql("select item_name,description from `tabItem` where name = '%s'" %(item_code), as_dict=1)
		ret = {
			'item_name' : item and item[0]['item_name'] or '',
			'description' : item and item[0]['description'] or ''
		}
		return ret
			
	def validate_serial_no(self):
		for d in getlist(self.doclist, 'maintenance_visit_details'):
			if d.serial_no and not webnotes.conn.sql("select name from `tabSerial No` where name = '%s' and docstatus != 2" % d.serial_no):
				msgprint("Serial No: "+ d.serial_no + " not exists in the system")
				raise Exception

	
	def validate(self):
		if not getlist(self.doclist, 'maintenance_visit_details'):
			msgprint("Please enter maintenance details")
			raise Exception

		self.validate_serial_no()
	
	def update_customer_issue(self, flag):
		for d in getlist(self.doclist, 'maintenance_visit_details'):
			if d.prevdoc_docname and d.prevdoc_doctype == 'Customer Issue' :
				if flag==1:
					mntc_date = self.doc.mntc_date
					service_person = d.service_person
					work_done = d.work_done
					if self.doc.completion_status == 'Fully Completed':
						status = 'Closed'
					elif self.doc.completion_status == 'Partially Completed':
						status = 'Work In Progress'
				else:
					nm = webnotes.conn.sql("select t1.name, t1.mntc_date, t2.service_person, t2.work_done from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2 where t2.parent = t1.name and t1.completion_status = 'Partially Completed' and t2.prevdoc_docname = %s and t1.name!=%s and t1.docstatus = 1 order by t1.name desc limit 1", (d.prevdoc_docname, self.doc.name))
					
					if nm:
						status = 'Work In Progress'
						mntc_date = nm and nm[0][1] or ''
						service_person = nm and nm[0][2] or ''
						work_done = nm and nm[0][3] or ''
					else:
						status = 'Open'
						mntc_date = ''
						service_person = ''
						work_done = ''
				
				webnotes.conn.sql("update `tabCustomer Issue` set resolution_date=%s, resolved_by=%s, resolution_details=%s, status=%s where name =%s",(mntc_date,service_person,work_done,status,d.prevdoc_docname))
	

	def check_if_last_visit(self):
		"""check if last maintenance visit against same sales order/ customer issue"""
		check_for_docname = check_for_doctype = None
		for d in getlist(self.doclist, 'maintenance_visit_details'):
			if d.prevdoc_docname:
				check_for_docname = d.prevdoc_docname
				check_for_doctype = d.prevdoc_doctype
		
		if check_for_docname:
			check = webnotes.conn.sql("select t1.name from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2 where t2.parent = t1.name and t1.name!=%s and t2.prevdoc_docname=%s and t1.docstatus = 1 and (t1.mntc_date > %s or (t1.mntc_date = %s and t1.mntc_time > %s))", (self.doc.name, check_for_docname, self.doc.mntc_date, self.doc.mntc_date, self.doc.mntc_time))
			
			if check:
				check_lst = [x[0] for x in check]
				check_lst =','.join(check_lst)
				msgprint("To cancel this, you need to cancel Maintenance Visit(s) "+cstr(check_lst)+" created after this maintenance visit against same "+check_for_doctype)
				raise Exception
			else:
				self.update_customer_issue(0)
	
	def on_submit(self):
		self.update_customer_issue(1)		
		webnotes.conn.set(self.doc, 'status', 'Submitted')
	
	def on_cancel(self):
		self.check_if_last_visit()		
		webnotes.conn.set(self.doc, 'status', 'Cancelled')

	def on_update(self):
		pass