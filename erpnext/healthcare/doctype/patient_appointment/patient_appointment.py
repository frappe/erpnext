# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json
from frappe.utils import getdate, add_days, get_time
from frappe.model.mapper import get_mapped_doc
from frappe import _
import datetime
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from erpnext.hr.doctype.employee.employee import is_holiday
from erpnext.healthcare.doctype.healthcare_settings.healthcare_settings import get_receivable_account, get_income_account
from erpnext.healthcare.utils import check_validity_exists, get_service_item_and_practitioner_charge

class PatientAppointment(Document):
	def validate(self):
		self.validate_overlaps()
		self.set_appointment_datetime()
		self.validate_customer_created()
		self.set_status()

	def after_insert(self):
		invoice_appointment(self)
		self.update_prescription_details()
		self.check_fee_validity()
		send_confirmation_msg(self)

	def set_status(self):
		today = getdate()
		appointment_date = getdate(self.appointment_date)

		# If appointment is created for today set status as Open else Scheduled
		if appointment_date == today:
			self.status = 'Open'
		elif appointment_date > today:
			self.status = 'Scheduled'
		elif appointment_date < today:
			self.status = 'Expired'

	def validate_overlaps(self):
		end_time = datetime.datetime.combine(getdate(self.appointment_date), get_time(self.appointment_time)) \
			 + datetime.timedelta(minutes=float(self.duration))

		overlaps = frappe.db.sql("""
		select
			name, practitioner, patient, appointment_time, duration
		from
			`tabPatient Appointment`
		where
			appointment_date=%s and name!=%s and status NOT IN ("Closed", "Cancelled")
			and (practitioner=%s or patient=%s) and
			((appointment_time<%s and appointment_time + INTERVAL duration MINUTE>%s) or
			(appointment_time>%s and appointment_time<%s) or
			(appointment_time=%s))
		""", (self.appointment_date, self.name, self.practitioner, self.patient,
		self.appointment_time, end_time.time(), self.appointment_time, end_time.time(), self.appointment_time))

		if overlaps:
			overlapping_details = _('Appointment overlaps with {0}').format(overlaps[0][0])
			overlapping_details += '<br>'
			overlapping_details += _('{0} has appointment scheduled with {1} at {2} having {3} minute(s) duration.').format(
				overlaps[0][1], overlaps[0][2], overlaps[0][3], overlaps[0][4])
			frappe.throw(overlapping_details, title=_('Appointments Overlapping'))

	def set_appointment_datetime(self):
		self.appointment_datetime = "%s %s" % (self.appointment_date, self.appointment_time or "00:00:00")

	def validate_customer_created(self):
		if frappe.db.get_single_value('Healthcare Settings', 'automate_appointment_invoicing'):
			if not frappe.db.get_value('Patient', self.patient, 'customer'):
				msg = _("Please create a Customer linked to the Patient")
				msg +=  " <b><a href='#Form/Patient/'>{0}</a></b>".format(self.patient)
				frappe.throw(msg, title=_('Customer Not Found'))

	def update_prescription_details(self):
		if self.procedure_prescription:
			frappe.db.set_value('Procedure Prescription', self.procedure_prescription, 'appointment_booked', 1)
			if self.procedure_template:
				comments = frappe.db.get_value('Procedure Prescription', self.procedure_prescription, 'comments')
				if comments:
					frappe.db.set_value('Patient Appointment', self.name, 'notes', comments)

	def check_fee_validity(self):
		# Check fee validity exists
		validity_exists = check_validity_exists(self.practitioner, self.patient)
		if validity_exists:
			fee_validity = frappe.get_doc('Fee Validity', validity_exists[0][0])

			# Check if the validity is valid
			appointment_date = getdate(self.appointment_date)
			if (fee_validity.valid_till >= appointment_date) and (fee_validity.visited < fee_validity.max_visit):
				visited = fee_validity.visited + 1
				frappe.db.set_value('Fee Validity', fee_validity.name, 'visited', visited)
				if fee_validity.ref_invoice:
					frappe.db.set_value('Patient Appointment', self.name, 'invoiced', True)
					frappe.db.set_value('Patient Appointment', self.name, 'ref_sales_invoice', fee_validity.ref_invoice)
				frappe.msgprint(_('{0} has fee validity till {1}').format(self.patient, fee_validity.valid_till))


def invoice_appointment(appointment_doc):
	if not appointment_doc.name:
		return

	if frappe.db.get_single_value('Healthcare Settings', 'automate_appointment_invoicing') and \
			not frappe.db.get_value('Patient Appointment', appointment_doc.name, 'invoiced'):
		sales_invoice = frappe.new_doc('Sales Invoice')
		sales_invoice.customer = frappe.get_value('Patient', appointment_doc.patient, 'customer')
		sales_invoice.appointment = appointment_doc.name
		sales_invoice.due_date = getdate()
		sales_invoice.is_pos = True
		sales_invoice.company = appointment_doc.company
		sales_invoice.debit_to = get_receivable_account(appointment_doc.company)

		item = sales_invoice.append('items', {})
		item = get_appointment_item(appointment_doc, item)

		payment = sales_invoice.append('payments', {})
		payment.mode_of_payment = appointment_doc.mode_of_payment
		payment.amount = appointment_doc.paid_amount

		sales_invoice.set_missing_values(for_validate=True)
		frappe.as_json('Sales Invoice')
		sales_invoice.save(ignore_permissions=True)
		sales_invoice.submit()
		frappe.msgprint(_('Sales Invoice {0} created as paid'.format(sales_invoice.name)), alert=True)
		frappe.db.set_value('Patient Appointment', appointment_doc.name, 'invoiced', True)
		frappe.db.set_value('Patient Appointment', appointment_doc.name, 'ref_sales_invoice', sales_invoice.name)


def get_appointment_item(appointment_doc, item):
	service_item, practitioner_charge = get_service_item_and_practitioner_charge(appointment_doc)
	item.item_code = service_item
	item.description = _('Consulting Charges: {0}').format(appointment_doc.practitioner)
	item.income_account = get_income_account(appointment_doc.practitioner, appointment_doc.company)
	item.rate = practitioner_charge
	item.amount = practitioner_charge
	item.qty = 1
	item.reference_dt = 'Patient Appointment'
	item.reference_dn = appointment_doc.name
	return item


def cancel_appointment(appointment_id):
	appointment = frappe.get_doc('Patient Appointment', appointment_id)
	# If invoiced --> fee_validity update visit as -1
	if appointment.invoiced:
		sales_invoice = check_sales_invoice_exists(appointment)
		if sales_invoice and cancel_sales_invoice(sales_invoice):
			frappe.msgprint(
				_('Appointment {0} and Sales Invoice {1} cancelled'.format(appointment.name, sales_invoice.name))
			)
		else:
			validity = check_validity_exists(appointment.practitioner, appointment.patient)
			if validity:
				fee_validity = frappe.get_doc('Fee Validity', validity)
				if validate_appointment_in_fee_validity(appointment, fee_validity.valid_till, fee_validity.ref_invoice):
					visited = fee_validity.visited - 1
					frappe.db.set_value('Fee Validity', fee_validity.name, 'visited', visited)
					frappe.msgprint(
						_('Appointment cancelled. Please review and cancel the invoice {0}'.format(fee_validity.ref_invoice))
					)
				else:
					frappe.msgprint(_('Appointment Cancelled'))
			else:
				frappe.msgprint(_('Appointment Cancelled'))
	else:
		frappe.msgprint(_('Appointment Cancelled'))


def validate_appointment_in_fee_validity(appointment, valid_end_date, ref_invoice):
	valid_days = frappe.db.get_single_value('Healthcare Settings', 'valid_days')
	max_visit = frappe.db.get_single_value('Healthcare Settings', 'max_visit')
	valid_start_date = add_days(getdate(valid_end_date), -int(valid_days))

	# Appointments which have same fee validity range with the appointment
	appointments = frappe.get_list('Patient Appointment', {
		'patient': appointment.patient,
		'invoiced': True,
		'appointment_date': ('<=', getdate(valid_end_date)),
		'appointment_date':('>=', getdate(valid_start_date)),
		'practitioner': appointment.practitioner
		}, order_by='appointment_date desc', limit=int(max_visit))

	if appointments and len(appointments) > 0:
		appointment_obj = appointments[len(appointments)-1]
		sales_invoice = check_sales_invoice_exists(appointment_obj)
		if sales_invoice.name == ref_invoice:
			return True
	return False


def cancel_sales_invoice(sales_invoice):
	if frappe.db.get_single_value('Healthcare Settings', 'automate_appointment_invoicing'):
		if len(sales_invoice.items) == 1:
			sales_invoice.cancel()
			return True
	return False


def check_si_item_exists(appointment):
	return frappe.db.exists(
		'Sales Invoice Item',
		{
			'reference_dt': 'Patient Appointment',
			'reference_dn': appointment.name
		}
	)


def check_sales_invoice_exists(appointment):
	si_item = check_si_item_exists(appointment)
	if si_item:
		sales_invoice = frappe.get_doc('Sales Invoice', frappe.db.get_value('Sales Invoice Item', si_item, 'parent'))
		return sales_invoice
	return False


@frappe.whitelist()
def get_availability_data(date, practitioner):
	"""
	Get availability data of 'practitioner' on 'date'
	:param date: Date to check in schedule
	:param practitioner: Name of the practitioner
	:return: dict containing a list of available slots, list of appointments and time of appointments
	"""

	date = getdate(date)
	weekday = date.strftime('%A')

	practitioner_doc = frappe.get_doc('Healthcare Practitioner', practitioner)

	check_employee_wise_availability(date, practitioner_doc)

	if practitioner_doc.practitioner_schedules:
		slot_details = get_available_slots(practitioner_doc.practitioner_schedules, date)
	else:
		frappe.throw(_('{0} does not have a Healthcare Practitioner Schedule. Add it in Healthcare Practitioner master').format(
			practitioner), title=_('Practitioner Schedule Not Found'))


	if not slot_details:
		# TODO: return available slots in nearby dates
		frappe.throw(_('Healthcare Practitioner not available on {0}').format(weekday), title=_('Not Available'))

	return {'slot_details': slot_details}


def check_employee_wise_availability(date, practitioner_doc):
	employee = None
	if practitioner_doc.employee:
		employee = practitioner_doc.employee
	elif practitioner_doc.user_id:
		employee = frappe.db.get_value('Employee', {'user_id': practitioner_doc.user_id}, 'name')

	if employee:
		# check holiday
		if is_holiday(employee, date):
			frappe.throw(_('{0} is a holiday'.format(date)), title=_('Not Available'))

		# check leave status
		leave_record = frappe.db.sql("""select half_day from `tabLeave Application`
			where employee = %s and %s between from_date and to_date
			and docstatus = 1""", (employee, date), as_dict=True)
		if leave_record:
			if leave_record[0].half_day:
				frappe.throw(_('{0} is on a Half day Leave on {1}').format(practitioner_doc.name, date), title=_('Not Available'))
			else:
				frappe.throw(_('{0} is on Leave on {1}').format(practitioner_doc.name, date), title=_('Not Available'))


def get_available_slots(practitioner_schedules, date):
	available_slots = []
	slot_details = []
	weekday = date.strftime('%A')
	practitioner = None

	for schedule_entry in practitioner_schedules:
		if schedule_entry.schedule:
			practitioner_schedule = frappe.get_doc('Practitioner Schedule', schedule_entry.schedule)
		else:
			frappe.throw(_('{0} does not have a Healthcare Practitioner Schedule. Add it in Healthcare Practitioner').format(
				frappe.bold(practitioner)), title=_('Practitioner Schedule Not Found'))

		if practitioner_schedule:
			available_slots = []
			for time_slot in practitioner_schedule.time_slots:
				if weekday == time_slot.day:
					available_slots.append(time_slot)

			if available_slots:
				appointments = []
				# fetch all appointments to practitioner by service unit
				filters = {
					'practitioner': practitioner,
					'service_unit': schedule_entry.service_unit,
					'appointment_date': date,
					'status': ['not in',['Cancelled']]
				}

				if schedule_entry.service_unit:
					slot_name  = schedule_entry.schedule + ' - ' + schedule_entry.service_unit
					allow_overlap = frappe.get_value('Healthcare Service Unit', schedule_entry.service_unit, 'overlap_appointments')
					if not allow_overlap:
						# fetch all appointments to service unit
						filters.pop('practitioner')
				else:
					slot_name = schedule_entry.schedule
					# fetch all appointments to practitioner without service unit
					filters['practitioner'] = practitioner
					filters['service_unit'] = ''

				appointments = frappe.get_all(
					'Patient Appointment',
					filters=filters,
					fields=['name', 'appointment_time', 'duration', 'status'])

				slot_details.append({'slot_name':slot_name, 'service_unit':schedule_entry.service_unit,
					'avail_slot':available_slots, 'appointments': appointments})

	return slot_details


@frappe.whitelist()
def update_status(appointment_id, status):
	frappe.db.set_value('Patient Appointment', appointment_id, 'status', status)
	appointment_booked = True
	if status == 'Cancelled':
		appointment_booked = False
		cancel_appointment(appointment_id)

	procedure_prescription = frappe.db.get_value('Patient Appointment', appointment_id, 'procedure_prescription')
	if procedure_prescription:
		frappe.db.set_value('Procedure Prescription', procedure_prescription, 'appointment_booked', appointment_booked)


def send_confirmation_msg(doc):
	if frappe.db.get_single_value('Healthcare Settings', 'send_appointment_confirmation'):
		message = frappe.db.get_single_value('Healthcare Settings', 'appointment_confirmation_msg')
		send_message(doc, message)


@frappe.whitelist()
def make_encounter(source_name, target_doc=None):
	doc = get_mapped_doc('Patient Appointment', source_name, {
		'Patient Appointment': {
			'doctype': 'Patient Encounter',
			'field_map': [
				['appointment', 'name'],
				['patient', 'patient'],
				['practitioner', 'practitioner'],
				['visit_department', 'department'],
				['patient_sex', 'patient_sex'],
				['encounter_date', 'appointment_date'],
				['invoiced', 'invoiced']
			]
		}
	}, target_doc)
	return doc


def send_appointment_reminder():
	if frappe.db.get_single_value('Healthcare Settings', 'send_appointment_reminder'):
		remind_before = datetime.datetime.strptime(frappe.db.get_single_value('Healthcare Settings', 'remind_before'), '%H:%M:%S')
		reminder_dt = datetime.datetime.now() + datetime.timedelta(
			hours=remind_before.hour, minutes=remind_before.minute, seconds=remind_before.second)

		appointment_list = frappe.db.get_all('Patient Appointment', {
			'appointment_datetime': ['between', (datetime.datetime.now(), reminder_dt)],
			'reminded': 0,
			'status': ['!=', 'Cancelled']
		})

		for appointment in appointment_list:
			doc = frappe.get_doc('Patient Appointment', appointment.name)
			message = frappe.db.get_single_value('Healthcare Settings', 'appointment_reminder_msg')
			send_message(doc, message)
			frappe.db.set_value('Patient Appointment', doc.name, 'reminded', 1)

def send_message(doc, message):
	patient = frappe.get_doc('Patient', doc.patient)
	if patient.mobile:
		context = {'doc': doc, 'alert': doc, 'comments': None}
		if doc.get('_comments'):
			context['comments'] = json.loads(doc.get('_comments'))

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
	conditions = get_event_conditions('Patient Appointment', filters)

	data = frappe.db.sql("""
		select
		`tabPatient Appointment`.name, `tabPatient Appointment`.patient,
		`tabPatient Appointment`.practitioner, `tabPatient Appointment`.status,
		`tabPatient Appointment`.duration,
		timestamp(`tabPatient Appointment`.appointment_date, `tabPatient Appointment`.appointment_time) as 'start',
		`tabAppointment Type`.color
		from
		`tabPatient Appointment`
		left join `tabAppointment Type` on `tabPatient Appointment`.appointment_type=`tabAppointment Type`.name
		where
		(`tabPatient Appointment`.appointment_date between %(start)s and %(end)s)
		and `tabPatient Appointment`.status != 'Cancelled' and `tabPatient Appointment`.docstatus < 2 {conditions}""".format(conditions=conditions),
		{"start": start, "end": end}, as_dict=True, update={"allDay": 0})

	for item in data:
		item.end = item.start + datetime.timedelta(minutes = item.duration)

	return data


@frappe.whitelist()
def get_procedure_prescribed(patient):
	return frappe.db.sql("""select pp.name, pp.procedure, pp.parent, ct.practitioner,
	ct.encounter_date, pp.practitioner, pp.date, pp.department
	from `tabPatient Encounter` ct, `tabProcedure Prescription` pp
	where ct.patient='{0}' and pp.parent=ct.name and pp.appointment_booked=0
	order by ct.creation desc""".format(patient))

def update_appointment_status():
	# update the status of appointments daily

	frappe.db.sql("""update `tabPatient Appointment` set status = 'Open'
		where appointment_date = CURDATE() and status = 'Scheduled'""")

	frappe.db.sql("""update `tabPatient Appointment` set status = 'Expired'
		where appointment_date < CURDATE() and status NOT IN ('Closed', 'Cancelled')""")