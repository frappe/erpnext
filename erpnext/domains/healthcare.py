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
			},
			{
				'fieldname': 'total_insurance_claim_amount', 'label': 'Total Insurance Claim Amount', 'fieldtype': 'Currency',
				'insert_after': 'total', 'read_only': True
			},
			{
				'fieldname': 'patient_payable_amount', 'label': 'Patient Payable Amount', 'fieldtype': 'Currency',
				'insert_after': 'total_insurance_claim_amount', 'read_only': True,
				'depends_on':'eval:doc.docstatus < 1 && doc.total_insurance_claim_amount && doc.total_insurance_claim_amount > 0'
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
			},
			{
				'fieldname': 'insurance_claim_coverage', 'label': 'Insurance Claim Coverage', 'fieldtype': 'Percent',
				'insert_after': 'amount', 'read_only': True
			},
			{
				'fieldname': 'insurance_claim_amount', 'label': 'Insurance Claim Amount', 'fieldtype': 'Currency',
				'insert_after': 'insurance_claim_coverage', 'read_only': True
			},
			{
				'fieldname': 'insurance_claim', 'label': 'Insurance Claim', 'fieldtype': 'Link',
				'read_only': True, 'insert_after': 'insurance_claim_amount', 'options': 'Healthcare Insurance Claim'
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
