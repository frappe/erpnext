# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import cstr

from frappe import msgprint

	

from erpnext.utilities.transaction_base import TransactionBase

class MaintenanceVisit(TransactionBase):
	
	def get_item_details(self, item_code):
		return frappe.db.get_value("Item", item_code, ["item_name", "description"], as_dict=1)
			
	def validate_serial_no(self):
		for d in self.get('maintenance_visit_details'):
			if d.serial_no and not frappe.db.exists("Serial No", d.serial_no):
				frappe.throw("Serial No: "+ d.serial_no + " not exists in the system")

	
	def validate(self):
		if not self.get('maintenance_visit_details'):
			msgprint("Please enter maintenance details")
			raise Exception

		self.validate_serial_no()
	
	def update_customer_issue(self, flag):
		for d in self.get('maintenance_visit_details'):
			if d.prevdoc_docname and d.prevdoc_doctype == 'Customer Issue' :
				if flag==1:
					mntc_date = self.mntc_date
					service_person = d.service_person
					work_done = d.work_done
					if self.completion_status == 'Fully Completed':
						status = 'Closed'
					elif self.completion_status == 'Partially Completed':
						status = 'Work In Progress'
				else:
					nm = frappe.db.sql("select t1.name, t1.mntc_date, t2.service_person, t2.work_done from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2 where t2.parent = t1.name and t1.completion_status = 'Partially Completed' and t2.prevdoc_docname = %s and t1.name!=%s and t1.docstatus = 1 order by t1.name desc limit 1", (d.prevdoc_docname, self.name))
					
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
				
				frappe.db.sql("update `tabCustomer Issue` set resolution_date=%s, resolved_by=%s, resolution_details=%s, status=%s where name =%s",(mntc_date,service_person,work_done,status,d.prevdoc_docname))
	

	def check_if_last_visit(self):
		"""check if last maintenance visit against same sales order/ customer issue"""
		check_for_docname = check_for_doctype = None
		for d in self.get('maintenance_visit_details'):
			if d.prevdoc_docname:
				check_for_docname = d.prevdoc_docname
				check_for_doctype = d.prevdoc_doctype
		
		if check_for_docname:
			check = frappe.db.sql("select t1.name from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2 where t2.parent = t1.name and t1.name!=%s and t2.prevdoc_docname=%s and t1.docstatus = 1 and (t1.mntc_date > %s or (t1.mntc_date = %s and t1.mntc_time > %s))", (self.name, check_for_docname, self.mntc_date, self.mntc_date, self.mntc_time))
			
			if check:
				check_lst = [x[0] for x in check]
				check_lst =','.join(check_lst)
				msgprint("To cancel this, you need to cancel Maintenance Visit(s) "+cstr(check_lst)+" created after this maintenance visit against same "+check_for_doctype)
				raise Exception
			else:
				self.update_customer_issue(0)
	
	def on_submit(self):
		self.update_customer_issue(1)		
		frappe.db.set(self, 'status', 'Submitted')
	
	def on_cancel(self):
		self.check_if_last_visit()		
		frappe.db.set(self, 'status', 'Cancelled')

	def on_update(self):
		pass