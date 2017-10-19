# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
from frappe.utils import getdate
from frappe import _
import datetime
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from erpnext.healthcare.doctype.healthcare_settings.healthcare_settings import get_receivable_account,get_income_account

class PatientAppointment(Document):
	def on_update(self):
		today = datetime.date.today()
		appointment_date = getdate(self.appointment_date)
		#If appointment created for today set as open
		if(today == appointment_date):
			frappe.db.set_value("Patient Appointment",self.name,"status","Open")
			self.reload()

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
					frappe.db.set_value("Patient Appointment",appointment.name,"sales_invoice",fee_validity.ref_invoice)
				frappe.msgprint(_("{0} has fee validity till {1}").format(appointment.patient, fee_validity.valid_till))
		confirm_sms(self)

def appointment_cancel(appointmentId):
	appointment = frappe.get_doc("Patient Appointment",appointmentId)
	#If invoice --> fee_validity update with -1 visit
	if (appointment.sales_invoice):
 		validity = frappe.db.exists({"doctype": "Fee Validity","ref_invoice": appointment.sales_invoice})
 		if(validity):
 			fee_validity = frappe.get_doc("Fee Validity",validity[0][0])
 			visited = fee_validity.visited - 1
 			frappe.db.set_value("Fee Validity",fee_validity.name,"visited",visited)
 			if visited <= 0:
 				frappe.msgprint(_("Appointment cancelled, Please review and cancel the invoice {0}".format(appointment.sales_invoice)))
 			else:
 				frappe.msgprint(_("Appointment cancelled"))

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
		frappe.throw(_("Physician not available on {0}").format(weekday))

	# if physician on leave return

	# if holiday return
	# if is_holiday(weekday):

	# get appointments on that day for physician
	appointments = frappe.get_all(
		"Patient Appointment",
		filters={"physician": physician, "appointment_date": date},
		fields=["name", "appointment_time", "duration", "status"])

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
def create_invoice(company, physician, patient, appointment_id, appointment_date):
	if not appointment_id:
		return False
	sales_invoice = frappe.new_doc("Sales Invoice")
	sales_invoice.customer = frappe.get_value("Patient", patient, "customer")
	sales_invoice.appointment = appointment_id
	sales_invoice.due_date = getdate()
	sales_invoice.is_pos = '0'
	sales_invoice.debit_to = get_receivable_account(company)

	fee_validity = get_fee_validity(physician, patient, appointment_date)
	create_invoice_items(appointment_id, physician, company, sales_invoice)

	sales_invoice.save(ignore_permissions=True)
	frappe.db.sql("""update `tabPatient Appointment` set sales_invoice=%s where name=%s""", (sales_invoice.name, appointment_id))
	frappe.db.set_value("Fee Validity", fee_validity.name, "ref_invoice", sales_invoice.name)
	consultation = frappe.db.exists({
			"doctype": "Consultation",
			"appointment": appointment_id})
	if consultation:
		frappe.db.set_value("Consultation", consultation[0][0], "invoice", sales_invoice.name)
	return sales_invoice.name

def get_fee_validity(physician, patient, date):
	validity_exist = validity_exists(physician, patient)
	if validity_exist :
		fee_validity = frappe.get_doc("Fee Validity",validity_exist[0][0])
		fee_validity = update_fee_validity(fee_validity, date)
	else:
		fee_validity = create_fee_validity(physician, patient, date)
	return fee_validity

def validity_exists(physician, patient):
	return frappe.db.exists({
			"doctype": "Fee Validity",
			"physician": physician,
			"patient": patient})

def update_fee_validity(fee_validity, date):
	max_visit = frappe.db.get_value("Healthcare Settings", None, "max_visit")
	valid_days = frappe.db.get_value("Healthcare Settings", None, "valid_days")
	if not valid_days:
		valid_days = 1
	if not max_visit:
		max_visit = 1
	date = getdate(date)
	valid_till = date + datetime.timedelta(days=int(valid_days))
	fee_validity.max_visit = max_visit
	fee_validity.visited = 1
	fee_validity.valid_till = valid_till
	fee_validity.save(ignore_permissions=True)
	return fee_validity

def create_fee_validity(physician, patient, date):
	fee_validity = frappe.new_doc("Fee Validity")
	fee_validity.physician = physician
	fee_validity.patient = patient
	fee_validity = update_fee_validity(fee_validity, date)
	return fee_validity

def create_invoice_items(appointment_id, physician, company, invoice):
	item_line = invoice.append("items")
	item_line.item_name = "Consulting Charges"
	item_line.description = "Consulting Charges:  " + physician
	item_line.qty = 1
	item_line.uom = "Nos"
	item_line.conversion_factor = 1
	item_line.income_account = get_income_account(physician,company)
	op_consulting_charge = frappe.db.get_value("Physician", physician, "op_consulting_charge")
	if op_consulting_charge:
		item_line.rate = op_consulting_charge
		item_line.amount = op_consulting_charge
	return invoice

@frappe.whitelist()
def create_consultation(appointment):
	appointment = frappe.get_doc("Patient Appointment",appointment)
	consultation = frappe.new_doc("Consultation")
	consultation.appointment = appointment.name
	consultation.patient = appointment.patient
	consultation.physician = appointment.physician
	consultation.visit_department = appointment.department
	consultation.patient_sex = appointment.patient_sex
	consultation.consultation_date = appointment.appointment_date
	if appointment.sales_invoice:
		consultation.invoice = appointment.sales_invoice
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
	data = frappe.db.sql("""select name, patient, physician, status,
		duration, timestamp(appointment_date, appointment_time) as
		'start' from `tabPatient Appointment` where
		(appointment_date between %(start)s and %(end)s)
		and docstatus < 2 {conditions}""".format(conditions=conditions),
		{"start": start, "end": end}, as_dict=True, update={"allDay": 0})
	for item in data:
		item.end = item.start + datetime.timedelta(minutes = item.duration)
	return data
