# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class DischargeSummary(Document):
	def on_submit(self):
		insert_ds_to_medical_record(self)
	def on_cancel(self):
		cancel_ds_from_medical_record(self)


def insert_ds_to_medical_record(doc):
	subject = set_subject_field(doc)
	medical_record = frappe.new_doc("Patient Medical Record")
	medical_record.patient = doc.patient
	medical_record.subject = subject
	medical_record.status = "Open"
	medical_record.communication_date = doc.discharge_date
	medical_record.reference_doctype = "Discharge Summary"
	medical_record.reference_name = doc.name
	medical_record.reference_owner = doc.owner
	medical_record.save(ignore_permissions=True)

def cancel_ds_from_medical_record(doc):
	medical_record_id = frappe.db.sql("select name from `tabPatient Medical Record` where reference_name=%s",(doc.name))

	if(medical_record_id[0][0]):
		frappe.delete_doc("Patient Medical Record", medical_record_id[0][0])

def set_subject_field(ds):
	subject = "Have no summary."
	if(ds.summary):
		subject = "Summary: \n"+ str(ds.summary)
	return subject
