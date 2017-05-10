# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, getdate, get_time, math
import time, json, datetime
from datetime import timedelta
from erpnext.healthcare.doctype.healthcare_settings.healthcare_settings import get_receivable_account

class Consultation(Document):
	def on_update(self):
		if(self.appointment):
			frappe.db.set_value("Appointment",self.appointment,"status","Closed")
		update_consultation_to_medical_record(self)

	def after_insert(self):
		insert_consultation_to_medical_record(self)

	def on_submit(self):
		if not self.diagnosis or not self.symptoms:
			frappe.throw("Diagnosis and Complaints cannot be left blank")

		physician = frappe.get_doc("Physician",self.physician)
		if(frappe.session.user != physician.user_id):
			frappe.throw(_("You don't have permission to submit"))

def set_sales_invoice_fields(company, patient):
	sales_invoice = frappe.new_doc("Sales Invoice")
	sales_invoice.customer = frappe.get_value("Patient", patient, "customer")
	# patient is custom field in sales inv.
	sales_invoice.due_date = getdate()
	sales_invoice.is_pos = '0'
	sales_invoice.debit_to = get_receivable_account(patient, company)

	return sales_invoice

def create_sales_invoice_item_lines(item, sales_invoice):
	sales_invoice_line = sales_invoice.append("items")
	sales_invoice_line.item_code = item.item_code
	sales_invoice_line.item_name =  item.item_name
	sales_invoice_line.qty = 1.0
	sales_invoice_line.description = item.description
	return sales_invoice_line

@frappe.whitelist()
def create_drug_invoice(company, patient, prescriptions):
	list_ids = json.loads(prescriptions)
	if not (company or patient or prescriptions):
		return False

	sales_invoice = set_sales_invoice_fields(company, patient)
	sales_invoice.update_stock = 1

	for line_id in list_ids:
		line_obj = frappe.get_doc("Drug Prescription", line_id)
		if line_obj:
			if(line_obj.drug_code):
				item = frappe.get_doc("Item", line_obj.drug_code)
				sales_invoice_line = create_sales_invoice_item_lines(item, sales_invoice)
				sales_invoice_line.qty = line_obj.get_quantity()
	#income_account and cost_center in itemlines - by set_missing_values()
	sales_invoice.set_missing_values()
	return sales_invoice.as_dict()

def insert_consultation_to_medical_record(doc):
	subject = set_subject_field(doc)
	medical_record = frappe.new_doc("Patient Medical Record")
	medical_record.patient = doc.patient
	medical_record.subject = subject
	medical_record.status = "Open"
	medical_record.communication_date = doc.consultation_date
	medical_record.reference_doctype = "Consultation"
	medical_record.reference_name = doc.name
	medical_record.reference_owner = doc.owner
	medical_record.save(ignore_permissions=True)

def update_consultation_to_medical_record(consultation):
	medical_record_id = frappe.db.sql("select name from `tabPatient Medical Record` where reference_name=%s",(consultation.name))
	if(medical_record_id[0][0]):
		subject = set_subject_field(consultation)
		frappe.db.set_value("Patient Medical Record",medical_record_id[0][0],"subject",subject)

def set_subject_field(consultation):
	subject = "No Diagnosis "
	if(consultation.diagnosis):
		subject = "Diagnosis: \n"+ str(consultation.diagnosis)+". "
	if(consultation.drug_prescription):
		subject +="\nDrug(s) Prescribed. "
	if(consultation.test_prescription):
		subject += " Test(s) Prescribed."

	return subject
