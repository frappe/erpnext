# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class InpatientMedicationTool(Document):
	pass

@frappe.whitelist()
def get_medication_orders(date):
	data = frappe.db.sql("""
		SELECT
			ip.inpatient_record, ip.patient, ip.patient_name,
			entry.drug, entry.drug_name, entry.dosage, entry.dosage_form, entry.time
		FROM
			`tabInpatient Medication Order` ip
		INNER JOIN
			`tabInpatient Medication Order Entry` entry
		ON
			ip.name = entry.parent
		WHERE
			entry.date = %(date)s
		ORDER BY
			entry.time
	""", {'date': date}, as_dict=1)

	for entry in data:
		inpatient_record = entry.inpatient_record
		entry['service_unit'] = get_current_healthcare_service_unit(inpatient_record)

		if entry['patient'] != entry['patient_name']:
			entry['patient'] = entry['patient'] + ' - ' + entry['patient_name']

		if entry['drug'] != entry['drug_name']:
			entry['drug'] = entry['drug'] + ' - ' + entry['drug_name']

	return data

def get_current_healthcare_service_unit(inpatient_record):
	ip_record = frappe.get_doc('Inpatient Record', inpatient_record)
	return ip_record.inpatient_occupancies[-1].service_unit

