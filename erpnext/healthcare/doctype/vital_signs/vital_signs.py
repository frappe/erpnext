# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cstr

class VitalSigns(Document):
	def on_submit(self):
		insert_vital_signs_to_medical_record(self)

	def on_cancel(self):
		delete_vital_signs_from_medical_record(self)

def insert_vital_signs_to_medical_record(doc):
	subject = set_subject_field(doc)
	medical_record = frappe.new_doc("Patient Medical Record")
	medical_record.patient = doc.patient
	medical_record.subject = subject
	medical_record.status = "Open"
	medical_record.communication_date = doc.signs_date
	medical_record.reference_doctype = "Vital Signs"
	medical_record.reference_name = doc.name
	medical_record.reference_owner = doc.owner
	medical_record.save(ignore_permissions=True)

def delete_vital_signs_from_medical_record(doc):
	medical_record_id = frappe.db.sql("select name from `tabPatient Medical Record` where reference_name=%s",(doc.name))
	if medical_record_id and medical_record_id[0][0]:
		frappe.delete_doc("Patient Medical Record", medical_record_id[0][0])

def set_subject_field(doc):
	subject = ""
	if(doc.temperature):
		subject += "Temperature: \n"+ cstr(doc.temperature)+". "
	if(doc.pulse):
		subject += "Pulse: \n"+ cstr(doc.pulse)+". "
	if(doc.respiratory_rate):
		subject += "Respiratory Rate: \n"+ cstr(doc.respiratory_rate)+". "
	if(doc.bp):
		subject += "BP: \n"+ cstr(doc.bp)+". "
	if(doc.bmi):
		subject += "BMI: \n"+ cstr(doc.bmi)+". "
	if(doc.nutrition_note):
		subject += "Note: \n"+ cstr(doc.nutrition_note)+". "

	return subject
