# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate
import json
from erpnext.healthcare.doctype.healthcare_settings.healthcare_settings import get_receivable_account,get_income_account

class Consultation(Document):
	def on_update(self):
		if(self.appointment):
			frappe.db.set_value("Patient Appointment",self.appointment,"status","Closed")
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
	sales_invoice.debit_to = get_receivable_account(company)

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

@frappe.whitelist()
def create_invoice(company, patient, physician, consultation_id):
	if not consultation_id:
		return False
	sales_invoice = frappe.new_doc("Sales Invoice")
	sales_invoice.customer = frappe.get_value("Patient", patient, "customer")
	sales_invoice.due_date = getdate()
	sales_invoice.is_pos = '0'
	sales_invoice.debit_to = get_receivable_account(company)

	create_invoice_items(physician, sales_invoice, company)

	sales_invoice.save(ignore_permissions=True)
	frappe.db.sql("""update tabConsultation set invoice=%s where name=%s""", (sales_invoice.name, consultation_id))
	appointment = frappe.db.get_value("Consultation", consultation_id, "appointment")
	if appointment:
		frappe.db.set_value("Patient Appointment", appointment, "sales_invoice", sales_invoice.name)
	return sales_invoice.name

def create_invoice_items(physician, invoice, company):
	item_line = invoice.append("items")
	item_line.item_name = "Consulting Charges"
	item_line.description = "Consulting Charges:  " + physician
	item_line.qty = 1
	item_line.uom = "Nos"
	item_line.conversion_factor = 1
	item_line.income_account = get_income_account(physician,company)
	op_consulting_charge = frappe.get_value("Physician",physician,"op_consulting_charge")
	if op_consulting_charge:
		item_line.rate = op_consulting_charge
		item_line.amount = op_consulting_charge
	return invoice

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
