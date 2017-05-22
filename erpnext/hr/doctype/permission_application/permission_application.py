# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import msgprint, _
from frappe.model.document import Document
from frappe.utils import get_time,get_datetime,getdate,flt, cint, add_months, date_diff, add_days
from frappe.utils import cint, cstr, date_diff, flt, formatdate, getdate, get_link_to_form, \
	comma_or, get_fullname
from erpnext.setup.doctype.sms_settings.sms_settings import send_sms

class PermissionApplication(Document):
	def validate(self):	
		self.validate_time()
		self.validate_deplcation()
		self.validate_max_permissions_per_month()
		self.validate_back_days()
		if self.total <=0 or not self.total:
			frappe.throw(_("Set Time from and to"))
		if self.reports_to != frappe.session.user and self.docstatus ==1:
			frappe.throw(_("You are not The Direct Manger"))
		if self.reports_to != frappe.session.user and self.docstatus ==0 and self.workflow_state != "Pending":
			self.workflow_state = "Pending"
			frappe.throw(_("You are not The Direct Manger"))
		
		if self.get("__islocal"):
			self.notify_leave_approver()

	def validate_back_days(self):
		from frappe.utils import getdate, nowdate
		user = frappe.session.user
		if getdate(self.permission_date) < getdate(nowdate()) and ("HR User" not in frappe.get_roles(user)):
			frappe.throw(_("Application can not be marked for past of the day"))
	
	def before_submit(self):
		if self.reports_to != frappe.session.user and self.docstatus ==0 and self.workflow_state != "Pending":
			frappe.throw(_("You are not The Direct Manger"))
		if self.status == "Open":
			frappe.throw(_("Please Change The Status of the document to Approved or Rejected"))

		self.validate_max_permissions_per_month()

		if self.reports_to != frappe.session.user:
			frappe.throw(_("You are not The Direct Manger"))

	def on_update_after_submit(self):
		user_roles = frappe.get_roles()		
		if "HR Manager" in user_roles:
			leave_list = frappe.get_list("Leave Application", fields=["name"] ,filters={"permission_application":self.name})
			if leave_list:
				frappe.db.sql("update `tabLeave Application` set docstatus =0  where name=%s", leave_list[0].name)
				frappe.delete_doc("Leave Application", leave_list[0].name)
				self.create_la()
			else :
				self.create_la()
		else:
			frappe.throw(_("No Permission"))
			
	def on_submit(self):
		self.validate_max_permissions_per_month()
		self.create_la()
		self.notify_employee(self.status)
		
	
	def create_la(self):
		pa = frappe.get_list("Permission Application", fields=["*"]
			, filters = {"employee":self.employee},ignore_permissions=True)
		
		if frappe.db.get_value("HR Settings", None, "max_permissions_per_month"):
			max = flt(frappe.db.get_value("HR Settings", None, "max_permissions_per_month"))
			if max:
				if (max >0):
					list =frappe.db.sql("""select sum(total) as total
						from `tabPermission Application`
						where employee = %(employee)s and docstatus =1
						and MONTH(permission_date) = MONTH(%(permission_date)s)
						and name != %(name)s 
						""", {
							"employee": self.employee,
							"permission_date": self.permission_date,
							"name": self.name
						}, as_dict = 1)
					Taken = -1
					v =0 
					if list[0]['total'] !=0:
						
						if flt(list[0]['total'])+self.total <= 2:
							Taken = -1
							print("111111111111111   ",list[0]['total'])
						elif flt(list[0]['total']) <2 and flt(list[0]['total'])+self.total >2:
							Taken=flt(list[0]['total'])+self.total-2
							v=2
							print("222222222  ",list[0]['total'])
						elif flt(list[0]['total']) >=2 and flt(list[0]['total'])+self.total <= max:
							Taken=flt(self.total)
							v=3
							print("3333333333   ",list[0]['total'])
					else :
						if self.total >2.0:
							Taken = flt(self.total-2)
							v=4
							print("55555555  ",list[0]['total'])
					
					
					if Taken != -1 :
						print("Taken ",Taken)
						la = frappe.new_doc("Leave Application",{})
						la.leave_type ='إجازة سنوية'
						la.from_date = self.permission_date
						la.to_date =self.permission_date
						la.half_day = 1
						la.total_leave_days = (Taken)/8.0
						la.employee = self.employee
						la.permission_application =self.name
						la.docstatus = 1
						la.status = "Approved"
						la.workflow_state = "خصم اذونات"
						la.company = "ٍٍSpeed Click"
						la.leave_approver = self.reports_to
						frappe.flags.ignore_account_permission = True
						frappe.flags.ignore_permission = True
						#~ la.flags.ignore_validate = True
						frappe.msgprint(str(self.permission_date))
						la.insert(ignore_permissions=True)
											
	def validate_time(self):
		if get_time(self.permission_time) > get_time(self.permission_time_to) :
			frappe.throw(_('to time must be bigger than from time '))
		
		d = get_datetime(self.permission_time_to) - get_datetime(self.permission_time)
		self.total = d.total_seconds()/60/60
		
		if frappe.db.get_value("HR Settings", None, "max_permissions_per_month"):
			if self.total >flt(frappe.db.get_value("HR Settings", None, "max_permissions_per_month")):
				frappe.throw(_('Max Permission Application Exced !'))
		

				
	def get_total(self):
		if self.permission_time_to and self.permission_time :
			d = get_datetime(self.permission_time_to) - get_datetime(self.permission_time)
			self.total = d.total_seconds()/60/60
		

	def validate_deplcation(self):
		list =frappe.db.sql("""select count(*)
			from `tabPermission Application`
			where employee = %(employee)s and docstatus =1
			and permission_date = %(permission_date)s
			and name != %(name)s
			""", {
				"name": self.name,
				"employee": self.employee,
				"permission_date": self.permission_date,
			}, as_dict = 1)
		if list[0]['count(*)']>0:
			frappe.throw(_('Permission Application already taken in this day'))

	def validate_max_permissions_per_month(self):
		if frappe.db.get_value("HR Settings", None, "max_permissions_per_month"):
			max = flt(frappe.db.get_value("HR Settings", None, "max_permissions_per_month"))
			
			if max:
				if (max >0):
					list =frappe.db.sql("""select sum(total) as total
						from `tabPermission Application`
						where employee = %(employee)s and docstatus =1
						and MONTH(permission_date) = MONTH(%(permission_date)s)
						and name != %(name)s 
						""", {
							"employee": self.employee,
							"permission_date": self.permission_date,
							"name": self.name,
						}, as_dict = 1)
					if list:
						if flt(list[0]['total'])+flt(self.total)>max:
							frappe.throw(_('Max Permission Application reashed for this month'+str(list[0]['total'])+str(self.total)))
		else:
			frappe.throw(_('Max Permission must allocated'))

	def get_employee (self):
		if self.get('__islocal'):
			employee = frappe.get_list("Employee", fields=["name","employee_name"]
			, filters = {"user_id":frappe.session.user},ignore_permissions=True)
			if employee:
				self.employee = employee[0].name
				self.employee_name = employee[0].employee_name

	def notify_employee(self, status):
		employee = frappe.get_doc("Employee", self.employee)
		if not employee.user_id:
			return

		def _get_message(url=False):
			if url:
				name = get_link_to_form(self.doctype, self.name)
			else:
				name = self.name

			message = "Permission Application: {name}".format(name=name)+"<br>"
			if self.workflow_state:
				message += "Workflow State: {workflow_state}".format(workflow_state=self.workflow_state)+"<br>"
			message += "Date: {permission_date}".format(permission_date=self.permission_date)+"<br>"
			message += "Total: {total}".format(total=self.total)+"<br>"
			message += "Status: {status}".format(status=_(status))
			return message
		
		def _get_sms(url=False):
			name = self.name
			employee_name = cstr(employee.employee_name)
			message = (_("%s") % (name))
			if self.workflow_state:
				message += "{workflow_state}".format(workflow_state=self.workflow_state)+"\n"
			message += (_("%s") % (employee_name))+"\n"
			message += (_("%s") % (self.permission_date))+" H \n"
			message += (_("%s") % (self.total))+"\n"
			return message
		
			
		self.notify({
			# for post in messages
			"message": _get_message(url=True),
			"message_to": employee.prefered_email,
			"subject": (_("Permission Application") + ": %s - %s") % (self.name, _(status))
		})
		send_sms([employee.cell_number], cstr(_get_sms(url=False)))

		
	def notify_leave_approver(self):
		employee = frappe.get_doc("Employee", self.employee)

		def _get_message(url=False):
			if url:
				name = get_link_to_form(self.doctype, self.name)
			else:
				name = self.name

			message = "Permission Application: {name}".format(name=name)+"<br>"
			if self.workflow_state:
				message += "Workflow State: {workflow_state}".format(workflow_state=self.workflow_state)+"<br>"
			message += "Date: {permission_date}".format(permission_date=self.permission_date)+"<br>"
			message += "Total: {total}".format(total=self.total)+"<br>"
			message += "Status: {status}".format(status=_(self.status))
			return message
		
		def _get_sms(url=False):
			name = self.name
			employee_name = cstr(employee.employee_name)
			message = (_("%s") % (name))
			if self.workflow_state:
				message += "{workflow_state}".format(workflow_state=self.workflow_state)+"\n"
			message += (_("%s") % (employee_name))+"\n"
			message += (_("%s") % (self.permission_date))+" H \n"
			message += (_("%s") % (self.total))+"\n"
			return message
		
		self.notify({
			# for post in messages
			"message": _get_message(url=True),
			"message_to": self.reports_to,

			# for email
			"subject": (_("New Permission Application") + ": %s - " + _("Employee") + ": %s") % (self.name, cstr(employee.employee_name))
		})
		try :
			la = frappe.get_doc("Employee", {"user_id":self.reports_to})
			send_sms([la.cell_number], cstr(_get_sms(url=False)))
		except:
			pass
	
	
	def notify(self, args):
		args = frappe._dict(args)
		from frappe.desk.page.chat.chat import post
		post(**{"txt": args.message, "contact": args.message_to, "subject": args.subject,
			"notify": cint(1)})

