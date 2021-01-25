# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import datetime
from frappe.model.document import Document
from frappe.utils import get_time, flt
from frappe.model.mapper import get_mapped_doc
from frappe import _
from frappe.utils import cstr, getdate, get_link_to_form
from erpnext.healthcare.doctype.healthcare_settings.healthcare_settings import get_receivable_account, get_income_account

class TherapySession(Document):
	def validate(self):
		self.validate_duplicate()
		self.set_total_counts()

	def validate_duplicate(self):
		end_time = datetime.datetime.combine(getdate(self.start_date), get_time(self.start_time)) \
			 + datetime.timedelta(minutes=flt(self.duration))

		overlaps = frappe.db.sql("""
		select
			name
		from
			`tabTherapy Session`
		where
			start_date=%s and name!=%s and docstatus!=2
			and (practitioner=%s or patient=%s) and
			((start_time<%s and start_time + INTERVAL duration MINUTE>%s) or
			(start_time>%s and start_time<%s) or
			(start_time=%s))
		""", (self.start_date, self.name, self.practitioner, self.patient,
		self.start_time, end_time.time(), self.start_time, end_time.time(), self.start_time))

		if overlaps:
			overlapping_details = _('Therapy Session overlaps with {0}').format(get_link_to_form('Therapy Session', overlaps[0][0]))
			frappe.throw(overlapping_details, title=_('Therapy Sessions Overlapping'))

	def on_submit(self):
		self.update_sessions_count_in_therapy_plan()

	def on_update(self):
		if self.appointment:
			frappe.db.set_value('Patient Appointment', self.appointment, 'status', 'Closed')

	def on_cancel(self):
		if self.appointment:
			frappe.db.set_value('Patient Appointment', self.appointment, 'status', 'Open')

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
