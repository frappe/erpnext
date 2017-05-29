from __future__ import unicode_literals
from frappe import _
import frappe
import datetime as dt

def get_data():

	return [
		{
			"label": _("Consultation"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "Patient Appointment",
					"description": _("Patient Appointment"),
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
					"description": _("Results"),
				},
				{
					"type": "doctype",
					"name": "Sample Collection",
					"label": _("Sample Collection"),
				},
				{
					"type": "doctype",
					"name": "Invoice Test Report",
					"description": _("Invoiced Results."),
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
					"label": "Physician",
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
					"label": "Medical Department"
				},
				{
					"type": "doctype",
					"name": "Appointment Type",
					"description": _("Appointment Type Master"),
				},
				{
					"type": "doctype",
					"name": "Prescription Dosage",
					"description": _("Prescription Dosage")
				},
				{
					"type": "doctype",
					"name": "Prescription Duration",
					"description": _("Prescription Period")
				},
				{
					"type": "doctype",
					"name": "Complaints",
					"description": _("Complaints")
				},
				{
					"type": "doctype",
					"name": "Diagnosis",
					"description": _("Diagnosis")
				},
				{
					"type": "doctype",
					"name": "Lab Test Samples",
					"description": _("Test Sample Master."),
				},
				{
					"type": "doctype",
					"name": "Lab Test UOM",
					"description": _("Lab Test UOM.")
				},
				{
					"type": "doctype",
					"name": "Antibiotics",
					"description": _("Antibiotics.")
				},
				{
					"type": "doctype",
					"name": "Sensitivity",
					"description": _("Sensitivity Naming.")
				},
				{
					"type": "doctype",
					"name": "Lab Test Template",
					"description": _("Lab Test Configurations.")
				}
			]
		}
	]
