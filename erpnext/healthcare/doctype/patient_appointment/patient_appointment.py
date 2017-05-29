# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import time, json
from frappe.utils import getdate, get_time
from frappe import msgprint, _
import datetime
from datetime import timedelta
import calendar
from erpnext.setup.doctype.sms_settings.sms_settings import send_sms
from erpnext.healthcare.scheduler import check_availability
from erpnext.healthcare.doctype.healthcare_settings.healthcare_settings import get_receivable_account,get_income_account

class PatientAppointment(Document):
	def on_update(self):
		today = datetime.date.today()
		appointment_date = getdate(self.appointment_date)
		#If appointment created for today set as open
		if(today == appointment_date):
			frappe.db.set_value("Patient Appointment",self.name,"status","Open")
			self.reload()

	def validate(self):
		pass
		# if not self.appointment_date:
		# 	frappe.throw(_("Please select date of appointment"))
		# if not self.end_dt:
		# 	physician = frappe.get_doc("Physician", self.physician)
		# 	if physician.schedule:
		# 		frappe.throw(_("Please use Check Availabilty to create Appointment"))

	def after_insert(self):
		#Check fee validity exists
		appointment = self
		validity_exist = validity_exists(appointment.physician, appointment.patient)
		if validity_exist :
			fee_validity = frappe.get_doc("Fee Validity",validity_exist[0][0])
			#Check if the validity is valid
			appointment_date = getdate(appointment.appointment_date)
			if((fee_validity.valid_till >= appointment_date) and (fee_validity.visited < fee_validity.max_visit)):
				visited = fee_validity.visited + 1
				frappe.db.set_value("Fee Validity",fee_validity.name,"visited",visited)
				if(fee_validity.ref_invoice):
					frappe.db.set_value("Patient Appointment",appointment.name,"invoiced",True)
					frappe.db.set_value("Patient Appointment",appointment.name,"invoice",fee_validity.ref_invoice)
				frappe.msgprint(_("{0} has fee validity till {1}").format(appointment.patient, fee_validity.valid_till))
		confirm_sms(self)

@frappe.whitelist()
def appointment_cancel(appointmentId):
	pass
	# appointment = frappe.get_doc("Patient Appointment",appointmentId)  
	#If invoiced --> fee_validity update with -1 visit
	# if(appointment.invoiced):
	# 	if (appointment.invoice):
	# 		validity = frappe.db.exists({"doctype": "Fee Validity","ref_invoice": appointment.invoice})
	# 		if(validity):
	# 			fee_validity = frappe.get_doc("Fee Validity",validity[0][0])
	# 			visited = fee_validity.visited - 1
	# 			frappe.db.set_value("Fee Validity",fee_validity.name,"visited",visited)
	# 			if visited <= 0:
	# 				frappe.msgprint(_("Appointment cancelled, Please review and cancel the invoice {0}".format(appointment.invoice)))
	# 			else:
	# 				frappe.msgprint(_("Appointment cancelled"))

@frappe.whitelist()
def check_availability_by_dept(department, date, time=None, end_dt=None):
	if not (department or date):
		frappe.msgprint(_("Please select Department and Date"))
	resources = frappe.db.sql(""" select name from `tabPhysician` where department= '%s' """ %(department))
	if resources:
		payload = {}
		for res in resources:
			payload[res[0]] = check_availability("Patient Appointment", "physician", True, "Physician", res[0], date, time, end_dt)
		return payload
	else:
		msgprint(_("No Physicians available for Department {0}").format(department))

@frappe.whitelist()
def check_availability_by_physician(physician, date, time=None, end_dt=None):
	if not (physician or date):
		frappe.throw(_("Please select Physician and Date"))
	payload = {}
	payload[physician] = check_availability("Patient Appointment", "physician", True, "Physician", physician, date, time, end_dt)
	return payload

@frappe.whitelist()
def check_appointment_availability(physician, date):
	print physician, date
	payload = {}
	payload[physician] = check_availability("Patient Appointment", "physician", True,
		"Physician", physician, date, None, None)
	return payload

@frappe.whitelist()
def get_availability_data(date, physician):
	# get availability data of 'physician' on 'date'
	date = getdate(date)
	weekday = date.strftime("%A")

	available_slots = []
	# get physicians schedule
	physician_schedule_name = frappe.db.get_value("Physician", physician, "physician_schedule")
	physician_schedule = frappe.get_doc("Physician Schedule", physician_schedule_name)
	time_per_appointment = frappe.db.get_value("Physician", physician, "time_per_appointment")

	for t in physician_schedule.time_slots:
		if weekday == t.day:
			available_slots.append(t)

	# if physician not available return 
	if not available_slots:
		# TODO: return available slots in nearby dates
		pass
		# frappe.throw(_("Physician not available on {0}").format(weekday))
	
	# if physician on leave return

	# if holiday return
	# if is_holiday(weekday):

	# get appointments on that day for physician
	appointments = frappe.get_all(
		"Patient Appointment",
		filters={"physician": physician, "appointment_date": date},
		fields=["name", "appointment_time", "duration"])
	
	return {
		"available_slots": available_slots,
		"appointments": appointments,
		"time_per_appointment": time_per_appointment
	}

@frappe.whitelist()
def update_status(appointmentId, status):
	frappe.db.set_value("Patient Appointment",appointmentId,"status",status)
	if(status=="Cancelled"):
		appointment_cancel(appointmentId)

@frappe.whitelist()
def set_open_appointments():
	today = getdate()
	frappe.db.sql("""update `tabPatient Appointment` set status='Open' where status = 'Scheduled' and appointment_date = %s""",(today))

@frappe.whitelist()
def set_pending_appointments():
	today = getdate()
	frappe.db.sql("""update `tabPatient Appointment` set status='Pending' where status in ('Scheduled','Open') and appointment_date < %s""",(today))

def confirm_sms(doc):
	if (frappe.db.get_value("Healthcare Settings", None, "app_con")=='1'):
		message = frappe.db.get_value("Healthcare Settings", None, "app_con_msg")
		send_message(doc, message)

@frappe.whitelist()
def create_invoice(company, patient, appointments):
	appointments = json.loads(appointments)
	if not appointments:
		return False
	sales_invoice = frappe.new_doc("Sales Invoice")
	sales_invoice.customer = frappe.get_value("Patient", patient, "customer")
	sales_invoice.due_date = getdate()
	validity_list = []
	sales_invoice.is_pos = '0'
	sales_invoice.debit_to = get_receivable_account(company)

	for appointment_id in appointments:
		appointment = frappe.get_doc("Patient Appointment",appointment_id)
		validity_exist = validity_exists(appointment.physician, appointment.patient)
		if validity_exist :
			fee_validity = frappe.get_doc("Fee Validity",validity_exist[0][0])
			fee_validity = update_fee_validity(fee_validity, appointment)
		else:
			fee_validity = create_fee_validity(appointment)
		validity_list.append(fee_validity.name)
		create_invoice_items(appointment, sales_invoice)

	sales_invoice.save(ignore_permissions=True)
	for appointment in appointments:
		frappe.db.sql(_("""update `tabPatient Appointment` set invoiced=1, invoice='{0}' where name='{1}'""").format(sales_invoice.name, appointment))
	for validity in validity_list:
		frappe.db.set_value("Fee Validity", validity, "ref_invoice", sales_invoice.name)
	return sales_invoice.name

def validity_exists(physician, patient):
	return frappe.db.exists({
			"doctype": "Fee Validity",
			"physician": physician,
			"patient": patient})

def update_fee_validity(fee_validity, appointment):
	max_visit = frappe.db.get_value("Healthcare Settings", None, "max_visit")
	valid_days = frappe.db.get_value("Healthcare Settings", None, "valid_days")
	if not valid_days:
		valid_days = 1
	if not max_visit:
		max_visit = 1
	date = appointment.appointment_date
	valid_till = date + datetime.timedelta(days=int(valid_days))
	fee_validity.max_visit = max_visit
	fee_validity.visited = 1
	fee_validity.valid_till = valid_till
	fee_validity.save(ignore_permissions=True)
	return fee_validity

def create_fee_validity(appointment):
	fee_validity = frappe.new_doc("Fee Validity")
	fee_validity.physician = appointment.physician
	fee_validity.patient = appointment.patient
	fee_validity = update_fee_validity(fee_validity, appointment)
	return fee_validity

def create_invoice_items(appointment, invoice):
	physician = frappe.get_doc("Physician",appointment.physician)
	item_line = invoice.append("items")
	item_line.item_name = "Consulting Charges"
	item_line.description = "Consulting Charges:  " + appointment.physician
	item_line.qty = 1
	item_line.uom = "Nos"
	item_line.conversion_factor = 1
	item_line.income_account = get_income_account(appointment.physician,appointment.company)
	item_line.rate = physician.op_consulting_charge
	item_line.amount = physician.op_consulting_charge
	return invoice

@frappe.whitelist()
def create_consultation(appointment):
	appointment = frappe.get_doc("Patient Appointment",appointment)
	consultation = frappe.new_doc("Consultation")
	consultation.appointment = appointment.name
	consultation.patient = appointment.patient
	consultation.physician = appointment.physician
	consultation.ref_physician = appointment.ref_physician
	consultation.visit_department = appointment.department
	consultation.patient_sex = appointment.patient_sex
	consultation.consultation_date = appointment.appointment_date
	return consultation.as_dict()

def remind_appointment():
	if (frappe.db.get_value("Healthcare Settings", None, "app_rem")=='1'):
		rem_before = datetime.datetime.strptime(frappe.get_value("Healthcare Settings", None, "rem_before"), "%H:%M:%S")
		rem_dt = datetime.datetime.now() + datetime.timedelta(hours = rem_before.hour, minutes=rem_before.minute, seconds= rem_before.second)

		appointment_list = frappe.db.sql("select name from `tabPatient Appointment` where start_dt between %s and %s and reminded = 0 ", (datetime.datetime.now(), rem_dt))

		for i in range (0,len(appointment_list)):
			doc = frappe.get_doc("Patient Appointment", appointment_list[i][0])
			message = frappe.db.get_value("Healthcare Settings", None, "app_rem_msg")
			send_message(doc, message)
			frappe.db.set_value("Patient Appointment",doc.name,"reminded",1)

def send_message(doc, message):
	patient = frappe.get_doc("Patient",doc.patient)
	if(patient.mobile):
		context = {"doc": doc, "alert": doc, "comments": None}
		if doc.get("_comments"):
			context["comments"] = json.loads(doc.get("_comments"))
		#jinja to string convertion happens here
		message = frappe.render_template(message, context)
		number = [patient.mobile]
		send_sms(number,message)

@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	from frappe.desk.calendar import get_event_conditions
	conditions = get_event_conditions("Patient Appointment", filters)
	data = frappe.db.sql("""select name, patient, physician, appointment_type, department, status, start_dt, end_dt
		from `tabPatient Appointment`
		where (start_dt between %(start)s and %(end)s)
				and docstatus < 2
				{conditions}
		""".format(conditions=conditions), {
			"start": start,
			"end": end
		}, as_dict=True, update={"allDay": 0})
	return data
