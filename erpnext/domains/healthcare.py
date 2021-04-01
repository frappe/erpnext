from __future__ import unicode_literals

data = {
	'desktop_icons': [
		'Patient',
		'Patient Appointment',
		'Patient Encounter',
		'Lab Test',
		'Healthcare',
		'Vital Signs',
		'Clinical Procedure',
		'Inpatient Record',
		'Accounts',
		'Buying',
		'Stock',
		'HR',
		'ToDo'
	],
	'default_portal_role': 'Patient',
	'restricted_roles': [
		'Healthcare Administrator',
		'LabTest Approver',
		'Laboratory User',
		'Nursing User',
		'Physician',
		'Patient'
	],
	'custom_fields': {
		'Sales Invoice': [
			{
				'fieldname': 'patient', 'label': 'Patient', 'fieldtype': 'Link', 'options': 'Patient',
				'insert_after': 'naming_series'
			},
			{
				'fieldname': 'patient_name', 'label': 'Patient Name', 'fieldtype': 'Data', 'fetch_from': 'patient.patient_name',
				'insert_after': 'patient', 'read_only': True
			},
			{
				'fieldname': 'ref_practitioner', 'label': 'Referring Practitioner', 'fieldtype': 'Link', 'options': 'Healthcare Practitioner',
				'insert_after': 'customer'
			}
		],
		'Sales Invoice Item': [
			{
				'fieldname': 'reference_dt', 'label': 'Reference DocType', 'fieldtype': 'Link', 'options': 'DocType',
				'insert_after': 'edit_references'
			},
			{
				'fieldname': 'reference_dn', 'label': 'Reference Name', 'fieldtype': 'Dynamic Link', 'options': 'reference_dt',
				'insert_after': 'reference_dt'
			}
		],
		'Stock Entry': [
			{
				'fieldname': 'inpatient_medication_entry', 'label': 'Inpatient Medication Entry', 'fieldtype': 'Link', 'options': 'Inpatient Medication Entry',
				'insert_after': 'credit_note', 'read_only': True
			}
		],
		'Stock Entry Detail': [
			{
				'fieldname': 'patient', 'label': 'Patient', 'fieldtype': 'Link', 'options': 'Patient',
				'insert_after': 'po_detail', 'read_only': True
			},
			{
				'fieldname': 'inpatient_medication_entry_child', 'label': 'Inpatient Medication Entry Child', 'fieldtype': 'Data',
				'insert_after': 'patient', 'read_only': True
			}
		]
	},
	'on_setup': 'erpnext.healthcare.setup.setup_healthcare'
}
