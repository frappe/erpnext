# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cstr
from frappe import _

class VitalSigns(Document):
	def on_submit(self):
		insert_vital_signs_to_medical_record(self)

	def on_cancel(self):
		delete_vital_signs_from_medical_record(self)

def insert_vital_signs_to_medical_record(doc):
	subject = set_subject_field(doc)
	medical_record = frappe.new_doc('Patient Medical Record')
	medical_record.patient = doc.patient
	medical_record.subject = subject
	medical_record.status = 'Open'
	medical_record.communication_date = doc.signs_date
	medical_record.reference_doctype = 'Vital Signs'
	medical_record.reference_name = doc.name
	medical_record.reference_owner = doc.owner
	medical_record.flags.ignore_mandatory = True
	medical_record.save(ignore_permissions=True)

def delete_vital_signs_from_medical_record(doc):
	medical_record = frappe.db.get_value('Patient Medical Record', {'reference_name': doc.name})
	if medical_record:
		frappe.delete_doc('Patient Medical Record', medical_record)

def set_subject_field(doc):
	subject = ''
	if doc.temperature:
		subject += frappe.bold(_('Temperature: ')) + cstr(doc.temperature) + '<br>'
	if doc.pulse:
		subject += frappe.bold(_('Pulse: ')) + cstr(doc.pulse) + '<br>'
	if doc.respiratory_rate:
		subject += frappe.bold(_('Respiratory Rate: ')) + cstr(doc.respiratory_rate) + '<br>'
	if doc.bp:
		subject += frappe.bold(_('BP: ')) + cstr(doc.bp) + '<br>'
	if doc.bmi:
		subject += frappe.bold(_('BMI: ')) + cstr(doc.bmi) + '<br>'
	if doc.nutrition_note:
		subject += frappe.bold(_('Note: ')) + cstr(doc.nutrition_note) + '<br>'

	return subject
