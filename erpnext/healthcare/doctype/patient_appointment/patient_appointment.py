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
from erpnext.hr.doctype.employee.employee import is_holiday

class PatientAppointment(Document):
	def on_update(self):
		today = datetime.date.today()
		appointment_date = getdate(self.appointment_date)

		# If appointment created for today set as open
		if today == appointment_date:
			frappe.db.set_value("Patient Appointment", self.name, "status", "Open")
			self.reload()

	def after_insert(self):
		if self.procedure_prescription:
			frappe.db.set_value("Procedure Prescription", self.procedure_prescription, "appointment_booked", True)
		# Check fee validity exists
		appointment = self
		validity_exist = validity_exists(appointment.physician, appointment.patient)
		if validity_exist:
			fee_validity = frappe.get_doc("Fee Validity", validity_exist[0][0])

			# Check if the validity is valid
			appointment_date = getdate(appointment.appointment_date)
			if (fee_validity.valid_till >= appointment_date) and (fee_validity.visited < fee_validity.max_visit):
				visited = fee_validity.visited + 1
				frappe.db.set_value("Fee Validity", fee_validity.name, "visited", visited)
				if fee_validity.ref_invoice:
					frappe.db.set_value("Patient Appointment", appointment.name, "sales_invoice", fee_validity.ref_invoice)
				frappe.msgprint(_("{0} has fee validity till {1}").format(appointment.patient, fee_validity.valid_till))
		confirm_sms(self)

	def create_invoice(self):
		return invoice_appointment(self)

def appointment_cancel(appointment_id):
	appointment = frappe.get_doc("Patient Appointment", appointment_id)

	# If invoice --> fee_validity update with -1 visit
	if appointment.sales_invoice:
		validity = frappe.db.exists({"doctype": "Fee Validity", "ref_invoice": appointment.sales_invoice})
		if validity:
			fee_validity = frappe.get_doc("Fee Validity", validity[0][0])
			visited = fee_validity.visited - 1
			frappe.db.set_value("Fee Validity", fee_validity.name, "visited", visited)
			if visited <= 0:
				frappe.msgprint(
					_("Appointment cancelled, Please review and cancel the invoice {0}".format(appointment.sales_invoice))
				)
			else:
				frappe.msgprint(_("Appointment cancelled"))


@frappe.whitelist()
def get_availability_data(date, physician):
	"""
	Get availability data of 'physician' on 'date'
	:param date: Date to check in schedule
	:param physician: Name of the physician
	:return: dict containing a list of available slots, list of appointments and time of appointments
	"""

	date = getdate(date)
	weekday = date.strftime("%A")

	available_slots = []
	slot_details = []
	physician_schedule = None

	employee = None

	physician_obj = frappe.get_doc("Physician", physician)

	# Get Physician employee relation
	if physician_obj.employee:
		employee = physician_obj.employee
	elif physician_obj.user_id:
		if frappe.db.exists({
			"doctype": "Employee",
			"user_id": physician_obj.user_id
			}):
			employee = frappe.get_doc("Employee", {"user_id": physician_obj.user_id}).name

	if employee:
		# Check if it is Holiday
		if is_holiday(employee, date):
			frappe.throw(_("{0} is a company holiday".format(date)))

		# Check if He/She on Leave
		leave_record = frappe.db.sql("""select half_day from `tabLeave Application`
			where employee = %s and %s between from_date and to_date
			and docstatus = 1""", (employee, date), as_dict=True)
		if leave_record:
			if leave_record[0].half_day:
				frappe.throw(_("Dr {0} on Half day Leave on {1}").format(physician, date))
			else:
				frappe.throw(_("Dr {0} on Leave on {1}").format(physician, date))

	# get physicians schedule
	if physician_obj.physician_schedules:
		for schedule in physician_obj.physician_schedules:
			if schedule.schedule:
				physician_schedule = frappe.get_doc("Physician Schedule", schedule.schedule)
			else:
				frappe.throw(_("Dr {0} does not have a Physician Schedule. Add it in Physician master".format(physician)))

			if physician_schedule:
				available_slots = []
				for t in physician_schedule.time_slots:
					if weekday == t.day:
						available_slots.append(t)

				if available_slots:
					appointments = []

					if schedule.service_unit:
						slot_name  = schedule.schedule+" - "+schedule.service_unit
						allow_overlap = frappe.get_value('Healthcare Service Unit', schedule.service_unit, 'overlap_appointments')
						if allow_overlap:
							# fetch all appointments to physician by service unit
							appointments = frappe.get_all(
								"Patient Appointment",
								filters={"physician": physician, "service_unit": schedule.service_unit, "appointment_date": date, "status": ["not in",["Cancelled"]]},
								fields=["name", "appointment_time", "duration", "status"])
						else:
							# fetch all appointments to service unit
							appointments = frappe.get_all(
								"Patient Appointment",
								filters={"service_unit": schedule.service_unit, "appointment_date": date, "status": ["not in",["Cancelled"]]},
								fields=["name", "appointment_time", "duration", "status"])
					else:
						slot_name = schedule.schedule
						# fetch all appointments to physician without service unit
						appointments = frappe.get_all(
							"Patient Appointment",
							filters={"physician": physician, "service_unit": '', "appointment_date": date, "status": ["not in",["Cancelled"]]},
							fields=["name", "appointment_time", "duration", "status"])

					slot_details.append({"slot_name":slot_name, "service_unit":schedule.service_unit,
						"avail_slot":available_slots, 'appointments': appointments})

	else:
		frappe.throw(_("Dr {0} does not have a Physician Schedule. Add it in Physician master".format(physician)))

	if not available_slots and not slot_details:
		# TODO: return available slots in nearby dates
		frappe.throw(_("Physician not available on {0}").format(weekday))

	return {
		"slot_details": slot_details
	}


@frappe.whitelist()
def update_status(appointment_id, status):
	frappe.db.set_value("Patient Appointment", appointment_id, "status", status)
	appointment_booked = True
	if status == "Cancelled":
		appointment_booked = False
		appointment_cancel(appointment_id)

	procedure_prescription = frappe.db.get_value("Patient Appointment", appointment_id, "procedure_prescription")
	if procedure_prescription:
		frappe.db.set_value("Procedure Prescription", procedure_prescription, "appointment_booked", appointment_booked)


@frappe.whitelist()
def set_open_appointments():
	today = getdate()
	frappe.db.sql(
		"update `tabPatient Appointment` set status='Open' where status = 'Scheduled'"
		" and appointment_date = %s", today)


@frappe.whitelist()
def set_pending_appointments():
	today = getdate()
	frappe.db.sql(
		"update `tabPatient Appointment` set status='Pending' where status in "
		"('Scheduled','Open') and appointment_date < %s", today)


def confirm_sms(doc):
	if frappe.db.get_value("Healthcare Settings", None, "app_con") == '1':
		message = frappe.db.get_value("Healthcare Settings", None, "app_con_msg")
		send_message(doc, message)


@frappe.whitelist()
def invoice_appointment(appointment_doc):
	if not appointment_doc.name:
		return False
	sales_invoice = frappe.new_doc("Sales Invoice")
	sales_invoice.customer = frappe.get_value("Patient", appointment_doc.patient, "customer")
	sales_invoice.appointment = appointment_doc.name
	sales_invoice.due_date = getdate()
	sales_invoice.is_pos = '0'
	sales_invoice.company = appointment_doc.company
	sales_invoice.debit_to = get_receivable_account(appointment_doc.company)

	fee_validity = get_fee_validity(appointment_doc.physician, appointment_doc.patient, appointment_doc.appointment_date)
	procedure_template = False
	if appointment_doc.procedure_template:
		procedure_template = appointment_doc.procedure_template
	create_invoice_items(appointment_doc.physician, appointment_doc.company, sales_invoice, procedure_template)

	sales_invoice.save(ignore_permissions=True)
	frappe.db.sql("""update `tabPatient Appointment` set sales_invoice=%s where name=%s""", (sales_invoice.name, appointment_doc.name))
	frappe.db.set_value("Fee Validity", fee_validity.name, "ref_invoice", sales_invoice.name)
	consultation = frappe.db.exists({
			"doctype": "Consultation",
			"appointment": appointment_doc.name})
	if consultation:
		frappe.db.set_value("Consultation", consultation[0][0], "invoice", sales_invoice.name)
	return sales_invoice.name


def get_fee_validity(physician, patient, date):
	validity_exist = validity_exists(physician, patient)
	if validity_exist:
		fee_validity = frappe.get_doc("Fee Validity", validity_exist[0][0])
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


def create_invoice_items(physician, company, invoice, procedure_template):
	item_line = invoice.append("items")
	if procedure_template:
		procedure_template_obj = frappe.get_doc("Clinical Procedure Template", procedure_template)
		item_line.item_code = procedure_template_obj.item_code
		item_line.item_name = procedure_template_obj.template
		item_line.description = procedure_template_obj.description
	else:
		item_line.item_name = "Consulting Charges"
		item_line.description = "Consulting Charges:  " + physician
		item_line.uom = "Nos"
		item_line.conversion_factor = 1
		item_line.income_account = get_income_account(physician, company)
		op_consulting_charge = frappe.db.get_value("Physician", physician, "op_consulting_charge")
		if op_consulting_charge:
			item_line.rate = op_consulting_charge
			item_line.amount = op_consulting_charge
	item_line.qty = 1


	return invoice


@frappe.whitelist()
def create_consultation(appointment):
	appointment = frappe.get_doc("Patient Appointment", appointment)
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
	if frappe.db.get_value("Healthcare Settings", None, "app_rem") == '1':
		rem_before = datetime.datetime.strptime(frappe.get_value("Healthcare Settings", None, "rem_before"), "%H:%M:%S")
		rem_dt = datetime.datetime.now() + datetime.timedelta(
			hours=rem_before.hour, minutes=rem_before.minute, seconds=rem_before.second)

		appointment_list = frappe.db.sql(
			"select name from `tabPatient Appointment` where start_dt between %s and %s and reminded = 0 ",
			(datetime.datetime.now(), rem_dt)
		)

		for i in range(0, len(appointment_list)):
			doc = frappe.get_doc("Patient Appointment", appointment_list[i][0])
			message = frappe.db.get_value("Healthcare Settings", None, "app_rem_msg")
			send_message(doc, message)
			frappe.db.set_value("Patient Appointment", doc.name, "reminded",1)


def send_message(doc, message):
	patient = frappe.get_doc("Patient", doc.patient)
	if patient.mobile:
		context = {"doc": doc, "alert": doc, "comments": None}
		if doc.get("_comments"):
			context["comments"] = json.loads(doc.get("_comments"))

		# jinja to string convertion happens here
		message = frappe.render_template(message, context)
		number = [patient.mobile]
		send_sms(number, message)


@frappe.whitelist()
def get_events(start, end, filters=None):
	"""Returns events for Gantt / Calendar view rendering.

	:param start: Start date-time.
	:param end: End date-time.
	:param filters: Filters (JSON).
	"""
	from frappe.desk.calendar import get_event_conditions
	conditions = get_event_conditions("Patient Appointment", filters)
	data = frappe.db.sql("""select `tabPatient Appointment`.name, patient, physician, status,
		duration, timestamp(appointment_date, appointment_time) as 'start', type.color as 'color'
    	from `tabPatient Appointment`
    	left join `tabAppointment Type` as type on `tabPatient Appointment`.appointment_type=type.name
    	where (appointment_date between %(start)s and %(end)s )
		and `tabPatient Appointment`.docstatus < 2 {conditions}""".format(conditions=conditions),
		{"start": start, "end": end}, as_dict=True, update={"allDay": 0})
	for item in data:
		item.end = item.start + datetime.timedelta(minutes = item.duration)

	return data
@frappe.whitelist()
def get_procedure_prescribed(patient):
	return frappe.db.sql("""select pp.name, pp.procedure, pp.parent, ct.physician,
	ct.consultation_date, pp.physician, pp.date, pp.department
	from tabConsultation ct, `tabProcedure Prescription` pp
	where ct.patient='{0}' and pp.parent=ct.name and pp.appointment_booked=0
	order by ct.creation desc""".format(patient))
