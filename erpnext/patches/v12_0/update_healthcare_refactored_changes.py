from __future__ import unicode_literals

import frappe
from frappe.model.utils.rename_field import rename_field
from frappe.modules import get_doctype_module, scrub

field_rename_map = {
	'Healthcare Settings': [
		['patient_master_name', 'patient_name_by'],
		['max_visit', 'max_visits'],
		['reg_sms', 'send_registration_msg'],
		['reg_msg', 'registration_msg'],
		['app_con', 'send_appointment_confirmation'],
		['app_con_msg', 'appointment_confirmation_msg'],
		['no_con', 'avoid_confirmation'],
		['app_rem', 'send_appointment_reminder'],
		['app_rem_msg', 'appointment_reminder_msg'],
		['rem_before', 'remind_before'],
		['manage_customer', 'link_customer_to_patient'],
		['create_test_on_si_submit', 'create_lab_test_on_si_submit'],
		['require_sample_collection', 'create_sample_collection_for_lab_test'],
		['require_test_result_approval', 'lab_test_approval_required'],
		['manage_appointment_invoice_automatically', 'automate_appointment_invoicing']
	],
	'Drug Prescription':[
		['use_interval', 'usage_interval'],
		['in_every', 'interval_uom']
	],
	'Lab Test Template':[
		['sample_quantity', 'sample_qty'],
		['sample_collection_details', 'sample_details']
	],
	'Sample Collection':[
		['sample_quantity', 'sample_qty'],
		['sample_collection_details', 'sample_details']
	],
	'Fee Validity': [
		['max_visit', 'max_visits']
	]
}

def execute():
	for dn in field_rename_map:
		if frappe.db.exists('DocType', dn):
			if dn == 'Healthcare Settings':
				frappe.reload_doctype('Healthcare Settings')
			else:
				frappe.reload_doc(get_doctype_module(dn), "doctype", scrub(dn))

	for dt, field_list in field_rename_map.items():
		if frappe.db.exists('DocType', dt):
			for field in field_list:
				if dt == 'Healthcare Settings':
					rename_field(dt, field[0], field[1])
				elif frappe.db.has_column(dt, field[0]):
					rename_field(dt, field[0], field[1])

	# first name mandatory in Patient
	if frappe.db.exists('DocType', 'Patient'):
		patients = frappe.db.sql("select name, patient_name from `tabPatient`", as_dict=1)
		frappe.reload_doc('healthcare', 'doctype', 'patient')
		for entry in patients:
			name = entry.patient_name.split(' ')
			frappe.db.set_value('Patient', entry.name, 'first_name', name[0])

	# mark Healthcare Practitioner status as Disabled
	if frappe.db.exists('DocType', 'Healthcare Practitioner'):
		practitioners = frappe.db.sql("select name from `tabHealthcare Practitioner` where 'active'= 0", as_dict=1)
		practitioners_lst = [p.name for p in practitioners]
		frappe.reload_doc('healthcare', 'doctype', 'healthcare_practitioner')
		if practitioners_lst:
			frappe.db.sql("update `tabHealthcare Practitioner` set status = 'Disabled' where name IN %(practitioners)s""", {"practitioners": practitioners_lst})

	# set Clinical Procedure status
	if frappe.db.exists('DocType', 'Clinical Procedure'):
		frappe.reload_doc('healthcare', 'doctype', 'clinical_procedure')
		frappe.db.sql("""
			UPDATE
				`tabClinical Procedure`
			SET
				docstatus = (CASE WHEN status = 'Cancelled' THEN 2
								WHEN status = 'Draft' THEN 0
								ELSE 1
							END)
		""")

	# set complaints and diagnosis in table multiselect in Patient Encounter
	if frappe.db.exists('DocType', 'Patient Encounter'):
		field_list = [
			['visit_department', 'medical_department'],
			['type', 'appointment_type']
		]
		encounter_details = frappe.db.sql("""select symptoms, diagnosis, name from `tabPatient Encounter`""", as_dict=True)
		frappe.reload_doc('healthcare', 'doctype', 'patient_encounter')
		frappe.reload_doc('healthcare', 'doctype', 'patient_encounter_symptom')
		frappe.reload_doc('healthcare', 'doctype', 'patient_encounter_diagnosis')

		for field in field_list:
			if frappe.db.has_column(dt, field[0]):
				rename_field(dt, field[0], field[1])

		for entry in encounter_details:
			doc = frappe.get_doc('Patient Encounter', entry.name)
			symptoms = entry.symptoms.split('\n') if entry.symptoms else []
			for symptom in symptoms:
				if not frappe.db.exists('Complaint', symptom):
					frappe.get_doc({
						'doctype': 'Complaint',
						'complaints': symptom
					}).insert()
				row = doc.append('symptoms', {
					'complaint': symptom
				})
				row.db_update()

			diagnosis = entry.diagnosis.split('\n') if entry.diagnosis else []
			for d in diagnosis:
				if not frappe.db.exists('Diagnosis', d):
					frappe.get_doc({
						'doctype': 'Diagnosis',
						'diagnosis': d
					}).insert()
				row = doc.append('diagnosis', {
					'diagnosis': d
				})
				row.db_update()
			doc.db_update()

	if frappe.db.exists('DocType', 'Fee Validity'):
		# update fee validity status
		frappe.db.sql("""
			UPDATE
				`tabFee Validity`
			SET
				status = (CASE WHEN visited >= max_visits THEN 'Completed'
								ELSE 'Pending'
							END)
		""")
