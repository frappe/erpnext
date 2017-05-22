# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe.utils import getdate, formatdate, nowdate
from frappe import throw, _
from frappe.utils import cint, cstr, date_diff, flt, formatdate, getdate, get_link_to_form, \
	comma_or, get_fullname
	
class AdvancePayment(Document):
	def validate(self):
		self.validate_date()
		self.valdate_duplicate()
		self.vaidate_amount()
		
		
	def before_submit(self):
		if self.status == "Open":
			frappe.throw(_("Please Change The Status of the document to Approved or Rejected"))
		
		
	def on_submit(self):
		self.notify_employee(self.status)
		#~ if self.status == "Open":
			#~ frappe.throw(_("Only Doc with status 'Approved' can be submitted"))
			
			
	def vaidate_amount(self):
		if self.employee :
			ss_employees = frappe.get_doc("Salary Structure Employee",{"employee":self.employee})
			self.base = ss_employees.base
			if self.amount > flt(ss_employees.base)/3.0:
				frappe.throw(_('Amount {0} is biger than Expected {1}').format(self.amount,flt(ss_employees.base)/3.0))
		
	
	def valdate_duplicate(self):
		ap_list = frappe.db.sql_list("""select amount from `tabAdvance Payment`
				where month=%s and name!=%s and status != 'Rejected' and employee = %s""", (self.month, self.name,self.employee))
		if ap_list:
			total = 0.0
			for ap in ap_list:
				total+= flt(ap)		
			if total+self.amount > self.base/3:
				frappe.throw(_('Total Month Amount {0} is biger than Expected {1}').format(total+self.amount,flt(self.base)/3.0))
			
			
				
			#~ frappe.throw(_('Duplicated Entry for Month {0} ').format(self.month))
		
	def validate_date(self):
		if getdate(self.date).day <20:
			frappe.throw(_('You Can not ask for Advance Payment before 20 of the month'))
		
		
	def get_base(self):
		if self.employee :
			ss_employees = frappe.get_doc("Salary Structure Employee",{"employee":self.employee})
			self.base = ss_employees.base
			self.amount = flt(ss_employees.base)/3.0
			self.month = getdate(self.date).month
		return {"base":self.base ,"amount":self.amount,"day":getdate(self.date).day}
	
	
	def notify_employee(self, status):
		employee = frappe.get_doc("Employee", self.employee)
		if not employee.user_id:
			return

		def _get_message(url=False):
			if url:
				name = get_link_to_form(self.doctype, self.name)
			else:
				name = self.name

			return (_("Advance Payment") + ": %s - %s") % (name, _(status))

		self.notify({
			# for post in messages
			"message": _get_message(url=True),
			"message_to": employee.user_id,
			"subject": _get_message(),
		})

	def notify(self, args):
		args = frappe._dict(args)
		from frappe.desk.page.chat.chat import post
		post(**{"txt": args.message, "contact": args.message_to, "subject": args.subject,
			"notify": cint(1)})
