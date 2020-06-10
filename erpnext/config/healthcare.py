from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
		{
			"label": _("Masters"),
			"items": [
				{
					"type": "doctype",
					"name": "Patient",
					"label": _("Patient"),
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Healthcare Practitioner",
					"label": _("Healthcare Practitioner"),
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Practitioner Schedule",
					"label": _("Practitioner Schedule"),
					"onboard": 1
				},
				{
					"type": "doctype",
					"name": "Medical Department",
					"label": _("Medical Department"),
				},
				{
					"type": "doctype",
					"name": "Healthcare Service Unit Type",
					"label": _("Healthcare Service Unit Type")
				},
				{
					"type": "doctype",
					"name": "Healthcare Service Unit",
					"label": _("Healthcare Service Unit")
				},
				{
					"type": "doctype",
					"name": "Medical Code Standard",
					"label": _("Medical Code Standard")
				},
				{
					"type": "doctype",
					"name": "Medical Code",
					"label": _("Medical Code")
				}
			]
		},
		{
			"label": _("Consultation Setup"),
			"items": [
				{
					"type": "doctype",
					"name": "Appointment Type",
					"label": _("Appointment Type"),
				},
				{
					"type": "doctype",
					"name": "Clinical Procedure Template",
					"label": _("Clinical Procedure Template")
				},
				{
					"type": "doctype",
					"name": "Prescription Dosage",
					"label": _("Prescription Dosage")
				},
				{
					"type": "doctype",
					"name": "Prescription Duration",
					"label": _("Prescription Duration")
				},
				{
					"type": "doctype",
					"name": "Antibiotic",
					"label": _("Antibiotic")
				}
			]
		},
		{
			"label": _("Consultation"),
			"items": [
				{
					"type": "doctype",
					"name": "Patient Appointment",
					"label": _("Patient Appointment")
				},
				{
					"type": "doctype",
					"name": "Clinical Procedure",
					"label": _("Clinical Procedure")
				},
				{
					"type": "doctype",
					"name": "Patient Encounter",
					"label": _("Patient Encounter")
				},
				{
					"type": "doctype",
					"name": "Vital Signs",
					"label": _("Vital Signs")
				},
				{
					"type": "doctype",
					"name": "Complaint",
					"label": _("Complaint")
				},
				{
					"type": "doctype",
					"name": "Diagnosis",
					"label": _("Diagnosis")
				},
				{
					"type": "doctype",
					"name": "Fee Validity",
					"label": _("Fee Validity")
				}
			]
		},
		{
			"label": _("Settings"),
			"items": [
				{
					"type": "doctype",
					"name": "Healthcare Settings",
					"label": _("Healthcare Settings"),
					"onboard": 1
				}
			]
		},
		{
			"label": _("Laboratory Setup"),
			"items": [
				{
					"type": "doctype",
					"name": "Lab Test Template",
					"label": _("Lab Test Template")
				},
				{
					"type": "doctype",
					"name": "Lab Test Sample",
					"label": _("Lab Test Sample")
				},
				{
					"type": "doctype",
					"name": "Lab Test UOM",
					"label": _("Lab Test UOM")
				},
				{
					"type": "doctype",
					"name": "Sensitivity",
					"label": _("Sensitivity")
				}
			]
		},
		{
			"label": _("Laboratory"),
			"items": [
				{
					"type": "doctype",
					"name": "Lab Test",
					"label": _("Lab Test")
				},
				{
					"type": "doctype",
					"name": "Sample Collection",
					"label": _("Sample Collection")
				},
				{
					"type": "doctype",
					"name": "Dosage Form",
					"label": _("Dosage Form")
				}
			]
		},
		{
			"label": _("Records and History"),
			"items": [
				{
					"type": "page",
					"name": "patient_history",
					"label": _("Patient History"),
				},
				{
					"type": "doctype",
					"name": "Patient Medical Record",
					"label": _("Patient Medical Record")
				},
				{
					"type": "doctype",
					"name": "Inpatient Record",
					"label": _("Inpatient Record")
				}
			]
		},
		{
			"label": _("Reports"),
			"items": [
				{
					"type": "report",
					"is_query_report": True,
					"name": "Patient Appointment Analytics",
					"doctype": "Patient Appointment"
				},
				{
					"type": "report",
					"is_query_report": True,
					"name": "Lab Test Report",
					"doctype": "Lab Test",
					"label": _("Lab Test Report")
				}
			]
		},
		{
			"label": _("Rehabilitation"),
			"icon": "icon-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Exercise Type",
					"label": _("Exercise Type")
				},
				{
					"type": "doctype",
					"name": "Exercise Difficulty Level",
					"label": _("Exercise Difficulty Level")
				},
				{
					"type": "doctype",
					"name": "Therapy Type",
					"label": _("Therapy Type")
				},
				{
					"type": "doctype",
					"name": "Therapy Plan",
					"label": _("Therapy Plan")
				},
				{
					"type": "doctype",
					"name": "Therapy Session",
					"label": _("Therapy Session")
				},
				{
					"type": "doctype",
					"name": "Motor Assessment Scale",
					"label": _("Motor Assessment Scale")
				}
			]
		}
	]
