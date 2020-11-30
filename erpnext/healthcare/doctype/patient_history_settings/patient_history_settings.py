# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr
from frappe.model.document import Document
from erpnext.healthcare.page.patient_history.patient_history import get_patient_history_doctypes

class PatientHistorySettings(Document):
	def validate(self):
		self.validate_date_fieldnames()

	def validate_date_fieldnames(self):
		for entry in self.custom_doctypes:
			field = frappe.get_meta(entry.document_type).get_field(entry.date_fieldname)
			if not field:
				frappe.throw(_('Row #{0}: No such Field named {1} found in the Document Type {2}.').format(
					entry.idx, frappe.bold(entry.date_fieldname), frappe.bold(entry.document_type)))

			if field.fieldtype not in ['Date', 'Datetime']:
				frappe.throw(_('Row #{0}: Field {1} in Document Type {2} is not a Date / Datetime field.').format(
					entry.idx, frappe.bold(entry.date_fieldname), frappe.bold(entry.document_type)))


def create_medical_record(doc, method=None):
	if frappe.flags.in_patch or frappe.flags.in_install or frappe.flags.in_setup_wizard or \
		frappe.db.get_value('Doctype', doc.doctype, 'module') != 'Healthcare':
		return

	if doc.doctype not in get_patient_history_doctypes():
		return

	subject = set_subject_field(doc)
	date_field = get_date_field(doc.doctype)
	medical_record = frappe.new_doc('Patient Medical Record')
	medical_record.patient = doc.patient
	medical_record.subject = subject
	medical_record.status = 'Open'
	medical_record.communication_date = doc.get(date_field)
	medical_record.reference_doctype = doc.doctype
	medical_record.reference_name = doc.name
	medical_record.reference_owner = doc.owner
	medical_record.save(ignore_permissions=True)


def set_subject_field(doc):
	from frappe.utils.formatters import format_value

	meta = frappe.get_meta(doc.doctype)
	subject = ''
	patient_history_fields = get_patient_history_fields(doc)

	for entry in patient_history_fields:
		fieldname = entry.get('fieldname')
		if entry.get('fieldtype') == 'Table' and doc.get(fieldname):
			formatted_value = get_formatted_value_for_table_field(doc.get(fieldname), meta.get_field(fieldname))
			subject += frappe.bold(_(entry.get('label')) + ': ') + '<br>' + cstr(formatted_value)

		else:
			if doc.get(fieldname):
				formatted_value = format_value(doc.get(fieldname), meta.get_field(fieldname), doc)
				subject += frappe.bold(_(entry.get('label')) + ': ') + cstr(formatted_value)

		subject += '<br>'

	return subject


def get_date_field(doctype):
	dt = get_patient_history_config_dt(doctype)

	return frappe.db.get_value(dt, { 'document_type': doctype }, 'date_fieldname')


def get_patient_history_fields(doc):
	import json
	dt = get_patient_history_config_dt(doc.doctype)
	patient_history_fields = frappe.db.get_value(dt, { 'document_type': doc.doctype }, 'selected_fields')

	if patient_history_fields:
		return json.loads(patient_history_fields)


def get_formatted_value_for_table_field(items, df):
	child_meta = frappe.get_meta(df.options)

	table_head = ''
	table_row = ''
	html = ''
	create_head = True
	for item in items:
		table_row += '<tr>'
		for cdf in child_meta.fields:
			if cdf.in_list_view:
				if create_head:
					table_head += '<td>' + cdf.label + '</td>'
				if item.get(cdf.fieldname):
					table_row += '<td>' + str(item.get(cdf.fieldname)) + '</td>'
				else:
					table_row += '<td></td>'
		create_head = False
		table_row += '</tr>'

	html += "<table class='table table-condensed table-bordered'>" + table_head +  table_row + "</table>"

	return html


def get_patient_history_config_dt(doctype):
	if frappe.db.get_value('DocType', doctype, 'custom'):
		return 'Patient History Custom Document Type'
	else:
		return 'Patient History Standard Document Type'
