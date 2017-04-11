# -*- coding: utf-8 -*-
# Copyright (c) 2017, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.medical.scheduler import check_availability
from frappe import msgprint, _
from frappe.utils import getdate
import datetime
import time, json
from erpnext.medical.doctype.op_settings.op_settings import get_receivable_account, get_income_account

class ProcedureAppointment(Document):
	def on_update(self):
		today = datetime.date.today()
		appointment_date = getdate(self.date)
		#If appointment created for today set as open
		if(today == appointment_date):
			frappe.db.set_value("Procedure Appointment", self.name, "status", "Open")
			self.reload()

	def validate(self):
		if(self.service_unit and self.service_type):
			service_unit = frappe.get_doc("Service Unit", self.service_unit)
			type_exist = frappe.db.exists({
				"doctype": "Service Type List",
				"parent": self.service_unit,
				"service_type": self.service_type})
			if not type_exist:
				frappe.throw(_("{0} can not be scheduled for {1}").format(self.service_type, self.service_unit))
			if(service_unit.avg_time or service_unit.schedule):
				if not self.end_dt:
					frappe.throw("Please use Check Availability to create Procedure Appointment")
			else:
				if(self.start_dt):
					frappe.db.set_value("Procedure Appointment", self.name, "end_dt", self.start_dt)

	def after_insert(self):
		if(self.prescription):
			frappe.db.sql("""update `tabProcedure Prescription` set scheduled = 1
			where name = %s""", (self.prescription))

@frappe.whitelist()
def btn_check_availability(service_type, date, time=None, end_dt=None):
	if not (service_type or date):
		frappe.msgprint(_("Please select Service Type and Date"))
	return check_availability_by_relation(service_type, date, time, end_dt)

def check_availability_by_relation(service_type, date, time=None, end_dt=None):
	resources = frappe.db.sql(""" select parent from `tabService Type List` where service_type= '%s' """ %(service_type))

	if resources:
		payload = {}
		for res in resources:
			payload[res[0]] = check_availability("Procedure Appointment", "service_unit", True, "Service Unit", res[0], date, time, end_dt)
		return payload
	else:
		msgprint(_("No Service Units for Service Type {0}").format(service_type))

@frappe.whitelist()
def get_procedures_rx(patient):
	return frappe.db.sql("""select name, procedure_template, parent, service_type, invoice from
	`tabProcedure Prescription` where patient='{0}' and scheduled = 0
	 order by parent desc""".format(patient))

@frappe.whitelist()
def update_status(appointmentId, status):
	frappe.db.set_value("Procedure Appointment",appointmentId,"status",status)
	if(status=="Cancelled"):
		appointment_cancel(appointmentId)

@frappe.whitelist()
def set_open_appointments():
	today = getdate()
	frappe.db.sql("""update `tabProcedure Appointment` set status='Open' where status = 'Scheduled' and date = %s""",(today))

@frappe.whitelist()
def set_pending_appointments():
	today = getdate()
	frappe.db.sql("""update `tabProcedure Appointment` set status='Pending' where status in ('Scheduled','Open') and date < %s""",(today))

@frappe.whitelist()
def appointment_cancel(appointmentId):
	invoice = frappe.get_value("Appointment", appointmentId, "invoice")
	if (invoice):
		frappe.msgprint(_("Appointment cancelled, Please review and cancel the invoice {0}".format(appointment.invoice)))

@frappe.whitelist()
def create_procedure(appointment):
	appointment = frappe.get_doc("Procedure Appointment",appointment)
	procedure = frappe.new_doc("Procedure")
	procedure.appointment = appointment.name
	procedure.patient = appointment.patient
	procedure.patient_age = appointment.patient_age
	procedure.patient_sex = appointment.patient_sex
	procedure.procedure_template = appointment.procedure_template
	procedure.service_type = appointment.service_type
	procedure.service_unit = appointment.service_unit
	procedure.start_dt = appointment.start_dt
	procedure.end_dt = appointment.end_dt
	procedure.token = appointment.token
	procedure.prescription = appointment.prescription
	procedure.invoice = appointment.invoice
	return procedure.as_dict()

def create_item_line(template, sales_invoice):
	if template:
		item = frappe.get_doc("Item", template)
		if item:
			if not item.disabled:
				sales_invoice_line = sales_invoice.append("items")
				sales_invoice_line.item_code = item.item_code
				sales_invoice_line.item_name =  item.item_name
				sales_invoice_line.qty = 1.0
				sales_invoice_line.description = item.description

@frappe.whitelist()
def create_invoice(company, patient, procedure_appointment, prescriptions):
	procedure_ids = json.loads(procedure_appointment)
	line_ids = json.loads(prescriptions)
	if not procedure_ids and not line_ids:
		return
	sales_invoice = frappe.new_doc("Sales Invoice")
	sales_invoice.customer = frappe.get_value("Patient", patient, "customer")
	sales_invoice.due_date = getdate()
	sales_invoice.patient = patient
	sales_invoice.is_pos = '0'
	sales_invoice.debit_to = get_receivable_account(patient, company)
	for line in line_ids:
		template = frappe.get_value("Procedure Prescription", line, "procedure_template")
		create_item_line(template, sales_invoice)
	for procedure_app in procedure_ids:
		template = frappe.get_value("Procedure Appointment", procedure_app, "procedure_template")
		create_item_line(template, sales_invoice)
	sales_invoice.set_missing_values()
	sales_invoice.save()
	#set invoice in lab test and prescription
	for item in procedure_ids:
		frappe.db.set_value("Procedure Appointment", item, "invoice", sales_invoice.name)
		frappe.db.sql("""update `tabProcedure Appointment` set invoiced = 1, invoice = %s
		where name = %s""", (sales_invoice.name, item))
		prescription = frappe.db.get_value("Procedure Appointment", item, "prescription")
		if prescription:
			frappe.db.set_value("Procedure Prescription", prescription, "invoice", sales_invoice.name)
	#set invoice in prescription
	for line in line_ids:
		frappe.db.set_value("Procedure Prescription", line, "invoice", sales_invoice.name)
	return sales_invoice.name
