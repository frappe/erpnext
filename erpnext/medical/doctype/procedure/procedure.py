# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.medical.scheduler import check_availability
from frappe import msgprint, _
from frappe.utils import getdate
import time, json
from erpnext.medical.doctype.op_settings.op_settings import get_receivable_account, get_income_account

class Procedure(Document):
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
					frappe.throw("Please use Check Availability to create Procedure")
			else:
				if(self.start_dt):
					frappe.db.set_value("Procedure", self.name, "end_dt", self.start_dt)

	def after_insert(self):
		if(self.prescription):
			frappe.db.sql("""update `tabProcedure Prescription` set scheduled = 1
			where name = %s""", (self.prescription))

@frappe.whitelist()
def check_available_on_date(service_unit, date, time=None, end_dt=None):
	if not (service_unit or date):
		frappe.msgprint(_("Please select Service Unit and Date"))
	return check_availability_by_resource("Procedure", "service_unit", True, "Service Unit", service_unit, date, time, end_dt)

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
			payload[res[0]] = check_availability("Procedure", "service_unit", True, "Service Unit", res[0], date, time, end_dt)
		return payload
	else:
		msgprint(_("No Service Units for Service Type {0}").format(service_type))

@frappe.whitelist()
def get_procedures(patient):
	return frappe.db.sql("""select name, procedure_template, parent, service_type, invoice from
	`tabProcedure Prescription` where patient='{0}' and scheduled = 0
	 order by parent desc""".format(patient))

@frappe.whitelist()
def get_procedures_by_sales_invoice(invoice):
	sales_invoice = frappe.get_doc("Sales Invoice", invoice)
	for item_line in sales_invoice.items:
		template_exist = frappe.db.exists({
			"doctype": "Procedure Template",
			"item": item_line.item_code
			})
		if template_exist :
			return frappe.db.sql("""select procedure_name, service_type from
			`tabProcedure Template` where item_code='{0}' """.format(item_line.item_code))

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
def create_invoice(company, patient, procedures, prescriptions):
	procedure_ids = json.loads(procedures)
	line_ids = json.loads(prescriptions)
	if not procedure_ids and not line_ids:
		return
	sales_invoice = frappe.new_doc("Sales Invoice")
	sales_invoice.customer = frappe.get_value("Patient", patient, "customer")
	sales_invoice.due_date = getdate()
	sales_invoice.is_pos = '0'
	sales_invoice.debit_to = get_receivable_account(patient, company)
	for line in line_ids:
		template = frappe.get_value("Procedure Prescription", line, "procedure_template")
		create_item_line(template, sales_invoice)
	for procedure in procedure_ids:
		template = frappe.get_value("Procedure", procedure, "procedure_template")
		create_item_line(template, sales_invoice)
	sales_invoice.set_missing_values()
	sales_invoice.save()
	#set invoice in lab test and prescription
	for item in procedure_ids:
		frappe.db.set_value("Procedure", item, "invoice", sales_invoice.name)
		frappe.db.sql("""update `tabProcedure` set invoiced = 1, invoice = %s
		where name = %s""", (sales_invoice.name, item))
		prescription = frappe.db.get_value("Procedure", item, "prescription")
		if prescription:
			frappe.db.set_value("Procedure Prescription", prescription, "invoice", sales_invoice.name)
	#set invoice in prescription
	for line in line_ids:
		frappe.db.set_value("Procedure Prescription", line, "invoice", sales_invoice.name)
	return sales_invoice.name
