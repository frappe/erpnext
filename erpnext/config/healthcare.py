from __future__ import unicode_literals
from frappe import _

def get_data():

	return [
		{
			"label": _("Consultation"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "Patient Appointment",
					"label": _("Patient Appointment"),
				},
				{
					"type": "doctype",
					"name": "Consultation",
					"label": _("Consultation"),
				},
				{
					"type": "doctype",
					"name": "Vital Signs",
					"label": _("Vital Signs"),
					"description": _("Record Patient Vitals"),
				},
				{
					"type": "page",
					"name": "medical_record",
					"label": _("Patient Medical Record"),
				},
				{
					"type": "page",
					"name": "appointment-analytic",
					"label": _("Appointment Analytics"),
				}
			]
		},
		{
			"label": _("Laboratory"),
			"icon": "icon-list",
			"items": [
				{
					"type": "doctype",
					"name": "Lab Test",
					"label": _("Lab Test"),
				},
				{
					"type": "doctype",
					"name": "Sample Collection",
					"label": _("Sample Collection"),
				},
				{
					"type": "report",
					"name": "Lab Test Report",
					"is_query_report": True,
					"label": _("Lab Test Report"),
				}
			]
		},
		{
			"label": _("Masters"),
			"icon": "icon-list",
			"items": [
				{
					"type": "doctype",
					"name": "Patient",
					"label": _("Patient"),
				},
				{
					"type": "doctype",
					"name": "Physician",
					"label": _("Physician"),
				},
				{
					"type": "doctype",
					"name": "Physician Schedule",
					"label": _("Physician Schedule"),
				},
				{
					"type": "doctype",
					"name": "Medical Code Standard",
					"label": _("Medical Code Standard"),
				},
				{
					"type": "doctype",
					"name": "Medical Code",
					"label": _("Medical Code"),
				},
				{
					"type": "doctype",
					"name": "Patient Service Unit",
					"label": _("Patient Service Unit")
				}
			]
		},
		{
			"label": _("Setup"),
			"icon": "icon-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Healthcare Settings",
					"label": _("Healthcare Settings"),
				},
				{
					"type": "doctype",
					"name": "Medical Department",
					"label": _("Medical Department"),
				},
				{
					"type": "doctype",
					"name": "Appointment Type",
					"label": _("Appointment Type"),
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
					"name": "Lab Test Sample",
					"label": _("Lab Test Sample"),
				},
				{
					"type": "doctype",
					"name": "Lab Test UOM",
					"label": _("Lab Test UOM")
				},
				{
					"type": "doctype",
					"name": "Antibiotic",
					"label": _("Antibiotic")
				},
				{
					"type": "doctype",
					"name": "Sensitivity",
					"label": _("Sensitivity")
				},
				{
					"type": "doctype",
					"name": "Lab Test Template",
					"label": _("Lab Test Template")
				}
			]
		}
	]
