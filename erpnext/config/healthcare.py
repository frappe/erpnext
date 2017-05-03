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
					"name": "Procedure",
					"description": _("Procedures"),
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
				{
					"type": "doctype",
					"name": "Patient Admission",
					"label": _("Patient Admission"),
					"description": _("Patient Admission"),
				},
				{
					"type": "doctype",
					"name": "Service Task",
					"label": _("Service Task"),
				},
				{
					"type": "doctype",
					"name": "Discharge Summary",
					"label": _("Discharge Summary"),
				}
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
			"label": _("OP/IP Setup"),
			"icon": "icon-cog",
			"items": [
				{
					"type": "doctype",
					"name": "Medical Department",
					"label": "Medical Department"
				},
				{
					"type": "doctype",
					"name": "Routine Observations",
					"label": _("Routine Observations"),
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
					"name": "Duration",
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
			"label": _("Infrastructure Setup"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "Zone",
					"label": _("Zone"),

				},
				{
					"type": "doctype",
					"name": "Facility",
					"label": _("Facility"),

				},
				{
					"type": "doctype",
					"name": "Facility Type",
					"label": _("Facility Type"),

				},
			]
		},
		{
			"label": _("Settings"),
			"icon": "icon-star",
			"items": [
				{
					"type": "doctype",
					"name": "OP Settings",
					"label": _("OP Settings"),
				},
				{
					"type": "doctype",
					"name": "IP Settings",
					"description": _("Settings for IP Module")
				},
				{
					"type": "doctype",
					"name": "Laboratory Settings",
					"description": _("Settings for Laboratory Module")
				},
				{
					"type": "doctype",
					"name": "PACS Settings",
					"description": _("Server Settings")
				},
			]
		},

	]
