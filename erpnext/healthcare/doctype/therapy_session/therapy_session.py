# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe import _
from frappe.utils import cstr, getdate
from erpnext.healthcare.doctype.healthcare_settings.healthcare_settings import get_receivable_account, get_income_account

class TherapySession(Document):
	def validate(self):
		self.set_total_counts()

	def on_submit(self):
		self.update_sessions_count_in_therapy_plan()
		insert_session_medical_record(self)

	def on_cancel(self):
		self.update_sessions_count_in_therapy_plan(on_cancel=True)

	def update_sessions_count_in_therapy_plan(self, on_cancel=False):
		therapy_plan = frappe.get_doc('Therapy Plan', self.therapy_plan)
		for entry in therapy_plan.therapy_plan_details:
			if entry.therapy_type == self.therapy_type:
				if on_cancel:
					entry.sessions_completed -= 1
				else:
					entry.sessions_completed += 1
		therapy_plan.save()

	def set_total_counts(self):
		target_total = 0
		counts_completed = 0
		for entry in self.exercises:
			if entry.counts_target:
				target_total += entry.counts_target
			if entry.counts_completed:
				counts_completed += entry.counts_completed

		self.db_set('total_counts_targeted', target_total)
		self.db_set('total_counts_completed', counts_completed)


@frappe.whitelist()
def create_therapy_session(source_name, target_doc=None):
	def set_missing_values(source, target):
		therapy_type = frappe.get_doc('Therapy Type', source.therapy_type)
		target.exercises = therapy_type.exercises

	doc = get_mapped_doc('Patient Appointment', source_name, {
			'Patient Appointment': {
				'doctype': 'Therapy Session',
				'field_map': [
					['appointment', 'name'],
					['patient', 'patient'],
					['patient_age', 'patient_age'],
					['gender', 'patient_sex'],
					['therapy_type', 'therapy_type'],
					['therapy_plan', 'therapy_plan'],
					['practitioner', 'practitioner'],
					['department', 'department'],
					['start_date', 'appointment_date'],
					['start_time', 'appointment_time'],
					['service_unit', 'service_unit'],
					['company', 'company'],
					['invoiced', 'invoiced']
				]
			}
		}, target_doc, set_missing_values)

	return doc


@frappe.whitelist()
def invoice_therapy_session(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.customer = frappe.db.get_value('Patient', source.patient, 'customer')
		target.due_date = getdate()
		target.debit_to = get_receivable_account(source.company)
		item = target.append('items', {})
		item = get_therapy_item(source, item)
		target.set_missing_values(for_validate=True)

	doc = get_mapped_doc('Therapy Session', source_name, {
			'Therapy Session': {
				'doctype': 'Sales Invoice',
				'field_map': [
					['patient', 'patient'],
					['referring_practitioner', 'practitioner'],
					['company', 'company'],
					['due_date', 'start_date']
				]
			}
		}, target_doc, set_missing_values)

	return doc


def get_therapy_item(therapy, item):
	item.item_code = frappe.db.get_value('Therapy Type', therapy.therapy_type, 'item')
	item.description = _('Therapy Session Charges: {0}').format(therapy.practitioner)
	item.income_account = get_income_account(therapy.practitioner, therapy.company)
	item.cost_center = frappe.get_cached_value('Company', therapy.company, 'cost_center')
	item.rate = therapy.rate
	item.amount = therapy.rate
	item.qty = 1
	item.reference_dt = 'Therapy Session'
	item.reference_dn = therapy.name
	return item


def insert_session_medical_record(doc):
	subject = frappe.bold(_('Therapy: ')) + cstr(doc.therapy_type) + '<br>'
	if doc.therapy_plan:
		subject += frappe.bold(_('Therapy Plan: ')) + cstr(doc.therapy_plan) + '<br>'
	if doc.practitioner:
		subject += frappe.bold(_('Healthcare Practitioner: ')) + doc.practitioner
	subject += frappe.bold(_('Total Counts Targeted: ')) + cstr(doc.total_counts_targeted) + '<br>'
	subject += frappe.bold(_('Total Counts Completed: ')) + cstr(doc.total_counts_completed) + '<br>'

	medical_record = frappe.new_doc('Patient Medical Record')
	medical_record.patient = doc.patient
	medical_record.subject = subject
	medical_record.status = 'Open'
	medical_record.communication_date = doc.start_date
	medical_record.reference_doctype = 'Therapy Session'
	medical_record.reference_name = doc.name
	medical_record.reference_owner = doc.owner
	medical_record.save(ignore_permissions=True)