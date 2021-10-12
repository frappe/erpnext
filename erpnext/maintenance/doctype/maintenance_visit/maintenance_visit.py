# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import get_datetime

from erpnext.utilities.transaction_base import TransactionBase


class MaintenanceVisit(TransactionBase):
	def get_feed(self):
		return _("To {0}").format(self.customer_name)

	def validate_serial_no(self):
		for d in self.get('purposes'):
			if d.serial_no and not frappe.db.exists("Serial No", d.serial_no):
				frappe.throw(_("Serial No {0} does not exist").format(d.serial_no))

	def validate_maintenance_date(self):
		if self.maintenance_type == "Scheduled" and self.maintenance_schedule_detail:
			item_ref = frappe.db.get_value('Maintenance Schedule Detail', self.maintenance_schedule_detail, 'item_reference')
			if item_ref:
				start_date, end_date = frappe.db.get_value('Maintenance Schedule Item', item_ref, ['start_date', 'end_date'])
				if get_datetime(self.mntc_date) < get_datetime(start_date) or get_datetime(self.mntc_date) > get_datetime(end_date):
					frappe.throw(_("Date must be between {0} and {1}").format(start_date, end_date))

	def validate(self):
		self.validate_serial_no()
		self.validate_maintenance_date()

	def update_completion_status(self):
		if self.maintenance_schedule_detail:
			frappe.db.set_value('Maintenance Schedule Detail', self.maintenance_schedule_detail, 'completion_status', self.completion_status)

	def update_actual_date(self):
		if self.maintenance_schedule_detail:
			frappe.db.set_value('Maintenance Schedule Detail', self.maintenance_schedule_detail, 'actual_date', self.mntc_date)

	def update_customer_issue(self, flag):
		if not self.maintenance_schedule:
			for d in self.get('purposes'):
				if d.prevdoc_docname and d.prevdoc_doctype == 'Warranty Claim' :
					if flag==1:
						mntc_date = self.mntc_date
						service_person = d.service_person
						work_done = d.work_done
						status = "Open"
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
							mntc_date = None
							service_person = None
							work_done = None

					wc_doc = frappe.get_doc('Warranty Claim', d.prevdoc_docname)
					wc_doc.update({
						'resolution_date': mntc_date,
						'resolved_by': service_person,
						'resolution_details': work_done,
						'status': status
					})

					wc_doc.db_update()

	def check_if_last_visit(self):
		"""check if last maintenance visit against same sales order/ Warranty Claim"""
		check_for_docname = None
		for d in self.get('purposes'):
			if d.prevdoc_docname:
				check_for_docname = d.prevdoc_docname
				#check_for_doctype = d.prevdoc_doctype

		if check_for_docname:
			check = frappe.db.sql("select t1.name from `tabMaintenance Visit` t1, `tabMaintenance Visit Purpose` t2 where t2.parent = t1.name and t1.name!=%s and t2.prevdoc_docname=%s and t1.docstatus = 1 and (t1.mntc_date > %s or (t1.mntc_date = %s and t1.mntc_time > %s))", (self.name, check_for_docname, self.mntc_date, self.mntc_date, self.mntc_time))

			if check:
				check_lst = [x[0] for x in check]
				check_lst =','.join(check_lst)
				frappe.throw(_("Cancel Material Visits {0} before cancelling this Maintenance Visit").format(check_lst))
				raise Exception
			else:
				self.update_customer_issue(0)

	def on_submit(self):
		self.update_customer_issue(1)
		frappe.db.set(self, 'status', 'Submitted')
		self.update_completion_status()
		self.update_actual_date()

	def on_cancel(self):
		self.check_if_last_visit()
		frappe.db.set(self, 'status', 'Cancelled')

	def on_update(self):
		pass
