# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr
from frappe.model.bean import getlist
from frappe import msgprint, throw, _

from erpnext.utilities.transaction_base import TransactionBase

class DocType(TransactionBase):
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def validate_serial_no(self):
		for d in getlist(self.doclist, 'maintenance_visit_details'):
			if d.serial_no and not frappe.conn.sql("""select name from `tabSerial No` where 
				name=%s and docstatus!=2""", d.serial_no):
					throw("{sr}: {serial_no} {not}".format(**{
						"sr": _("Serial No"),
						"serial_no": d.serial_no,
						"not": _("does not exists in the system")
					}))

	def validate(self):
		if not getlist(self.doclist, 'maintenance_visit_details'):
			throw(_("Please enter maintenance details"))

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
					nm = frappe.conn.sql("""select mv.name, mv.mntc_date, mvp.service_person, 
						mvp.work_done from `tabMaintenance Visit` mv, `tabMaintenance Visit Purpose` mvp 
						where mvp.parent=mv.name and mv.completion_status='Partially Completed' 
						and mvp.prevdoc_docname=%s and mv.name!=%s and mv.docstatus=1 
						order by mv.name desc limit 1""", (d.prevdoc_docname, self.doc.name))

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

				frappe.conn.sql("""update `tabCustomer Issue` set resolution_date=%s, resolved_by=%s, 
					resolution_details=%s, status=%s where name=%s""", 
					(mntc_date, service_person, work_done, status, d.prevdoc_docname))

	def check_if_last_visit(self):
		"""check if last maintenance visit against same sales order / customer issue"""
		check_for_docname = check_for_doctype = None
		for d in getlist(self.doclist, 'maintenance_visit_details'):
			if d.prevdoc_docname:
				check_for_docname = d.prevdoc_docname
				check_for_doctype = d.prevdoc_doctype

		if check_for_docname:
			check = frappe.conn.sql("""select mv.name from `tabMaintenance Visit` mv, 
				`tabMaintenance Visit Purpose` mvp where mvp.parent=mv.name and mv.name!=%s and 
				mvp.prevdoc_docname=%s and mv.docstatus=1 and 
				(mv.mntc_date>%s or (mv.mntc_date=%s and mv.mntc_time>%s))""", 
				(self.doc.name, check_for_docname, self.doc.mntc_date, self.doc.mntc_date, 
				self.doc.mntc_time))

			if check:
				check_lst = [x[0] for x in check]
				check_lst =','.join(check_lst)
				throw("{cancel} {list} {after} {visit}".format(**{
					"cancel": _("To cancel this, you need to cancel Maintenance Visit(s)"),
					"list": cstr(check_lst),
					"after": _("created after this maintenance visit against same"),
					"visit": check_for_doctype
				}))
			else:
				self.update_customer_issue(0)

	def on_submit(self):
		self.update_customer_issue(1)
		frappe.conn.set(self.doc, 'status', 'Submitted')

	def on_cancel(self):
		self.check_if_last_visit()
		frappe.conn.set(self.doc, 'status', 'Cancelled')

	def on_update(self):
		pass

@frappe.whitelist()
def get_item_details(item_code):
	return frappe.conn.get_value("Item", item_code, ["item_name", "description"], as_dict=1)