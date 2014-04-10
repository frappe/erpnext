# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.utils import cstr, flt, getdate

from frappe import msgprint, _
from frappe.model.mapper import get_mapped_doc
from frappe.model.document import Document

class Appraisal(Document):
	def validate(self):
		if not self.status:
			self.status = "Draft"

		self.validate_dates()
		self.validate_existing_appraisal()
		self.calculate_total()

	def get_employee_name(self):
		self.employee_name = frappe.db.get_value("Employee", self.employee, "employee_name")
		return self.employee_name
		
	def validate_dates(self):
		if getdate(self.start_date) > getdate(self.end_date):
			frappe.throw(_("End Date can not be less than Start Date"))
	
	def validate_existing_appraisal(self):
		chk = frappe.db.sql("""select name from `tabAppraisal` where employee=%s 
			and (status='Submitted' or status='Completed') 
			and ((start_date>=%s and start_date<=%s) 
			or (end_date>=%s and end_date<=%s))""",
			(self.employee,self.start_date,self.end_date,self.start_date,self.end_date))
		if chk:
			frappe.throw("You have already created Appraisal "\
				+cstr(chk[0][0])+" in the current date range for employee "\
				+cstr(self.employee_name))
	
	def calculate_total(self):
		total, total_w  = 0, 0
		for d in self.get('appraisal_details'):
			if d.score:
				d.score_earned = flt(d.score) * flt(d.per_weightage) / 100
				total = total + d.score_earned
			total_w += flt(d.per_weightage)

		if int(total_w) != 100:
			msgprint("Total weightage assigned should be 100%. It is :" + str(total_w) + "%", 
				raise_exception=1)

		if frappe.db.get_value("Employee", self.employee, "user_id") != \
				frappe.session.user and total == 0:
			msgprint("Total can't be zero. You must atleast give some points!", raise_exception=1)

		self.total_score = total
			
	def on_submit(self):
		frappe.db.set(self, 'status', 'Submitted')
	
	def on_cancel(self): 
		frappe.db.set(self, 'status', 'Cancelled')

@frappe.whitelist()
def fetch_appraisal_template(source_name, target_doc=None):
	target_doc = get_mapped_doc("Appraisal Template", source_name, {
		"Appraisal Template": {
			"doctype": "Appraisal", 
		}, 
		"Appraisal Template Goal": {
			"doctype": "Appraisal Goal", 
		}
	}, target_doc)

	return target_doc