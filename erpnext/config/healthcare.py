from __future__ import unicode_literals
from frappe import _
import frappe
import datetime as dt

def get_data():

	return [
		{
			"label": _("Documents"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "Appointment",
					"description": _("Patient Appointment"),
				},
				{
					"type": "doctype",
					"name": "Vital Signs",
					"label": _("Vital Signs"),
					"description": _("Record Patient Vitals"),
				},
				{
					"type": "doctype",
					"name": "Consultation",
					"label": _("Consultation"),
				},
				{
					"type": "doctype",
					"name": "Procedure Appointment",
					"description": _("Procedure Appointments"),
				},
				{
					"type": "doctype",
					"name": "Clinical Procedure",
					"description": _("Clinical Procedures"),
				},
				{
					"type": "doctype",
					"name": "Sample Collection",
					"label": _("Sample Collection"),
				},
				{
					"type": "doctype",
					"name": "Lab Test",
					"description": _("Results"),
				},
			]
		},
		{
			"label": _("Tools"),
			"icon": "icon-list",
			"items": [
				{
					"type": "page",
					"name": "medical_record",
					"label": _("Patient Medical Record"),
				},
				{
					"type": "page",
					"name": "appointment-desk",
					"label": _("Appointment Desk"),
				},
				{
					"type": "page",
					"name": "service-desk",
					"label": _("Service Desk"),
				},
				{
					"type": "doctype",
					"name": "Invoice Test Report",
					"description": _("Invoiced Results."),
				},
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
				},
				{
					"type": "doctype",
					"name": "Referring Physician",
					"description": _("Referring Physician"),
				},
				{
					"type": "doctype",
					"name": "Service Unit",
					"label": _("Service Unit"),

				},
			]
		},
		{
			"label": _("Reports"),
			"icon": "icon-list",
			"items": [
				{
					"type": "page",
					"name": "appointment-analytic",
					"label": _("Appointment Analytics"),
				},
				{
					"type": "report",
					"name": "Lab Test Report",
					"is_query_report": True,
					"doctype": "Lab Test"
				},

			]
		},
		{
			"label": _("OP Setup"),
			"icon": "icon-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Medical Department",
					"label": "Medical Department"
				},
				{
					"type": "doctype",
					"name": "Procedure Template",
					"label": _("Procedure Template"),
				},
				{
					"type": "doctype",
					"name": "Service Type",
					"label": _("Service Type"),
				},
				{
					"type": "doctype",
					"name": "Dosage",
					"description": _("Drug Prescription Dosage")
				},
				{
					"type": "doctype",
					"name": "Drug Prescription Duration",
					"description": _("Drug Prescription Period")
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
					"name": "Appointment Type",
					"description": _("Appointment Type Master"),
				},
			]
		},
		{
			"label": _("Laboratory Setup"),
			"icon": "icon-cog",
			"items": [
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
		},
		{
			"label": _("Settings"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "Healthcare Settings",
					"label": _("Healthcare Settings"),
				}
			]
		},

	]
