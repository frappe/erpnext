# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class PatientMedicalRecord(Document):
	pass

def insert_attachment(doc, patient):
	subject = str(doc.file_name)
	medical_record = frappe.new_doc("Patient Medical Record")
	medical_record.patient = patient
	medical_record.subject = subject
	medical_record.status = "Open"
	medical_record.communication_date = doc.creation
	medical_record.reference_doctype = "File"
	medical_record.reference_name = doc.name
	medical_record.reference_owner = doc.owner
	medical_record.save(ignore_permissions=True)

def delete_attachment(ref_dt, dt):
	#delete scheduled records
	frappe.db.sql("delete from `tabPatient Medical Record` where reference_doctype=%s and patient=%s", (ref_dt,dt))
