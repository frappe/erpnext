import frappe
from frappe.model.rename_doc import rename_doc
from frappe.model.utils.rename_field import rename_field
from frappe.modules import scrub, get_doctype_module

field_rename_map = {
	"Encounter": [
		["consultation_time", "encounter_time"],
		["consultation_date", "encounter_date"],
		["consultation_comment", "encounter_comment"],
		["physician", "practitioner"]
	],
	"Practitioner": [
		["physician_schedules", "practitioner_schedules"]
	],
	"Fee Validity": [
		["physician", "practitioner"]
	],
	"Lab Test": [
		["physician", "practitioner"]
	],
	"Patient Appointment": [
		["physician", "practitioner"],
		["referring_physician", "referring_practitioner"]
	],
	"Procedure Prescription": [
		["physician", "practitioner"]
	]
}

doc_rename_map = {
	"Physician Schedule Time Slot": "Healthcare Schedule Time Slot",
	"Physician Schedule": "Practitioner Schedule",
	"Physician Service Unit Schedule": "Practitioner Service Unit Schedule",
	"Consultation": "Encounter",
	"Physician": "Practitioner"
}

def execute():
	domain_settings = frappe.get_doc('Domain Settings')
	active_domains = [d.domain for d in domain_settings.active_domains]

	if "Healthcare" in active_domains:
		for dt in doc_rename_map:
			if frappe.db.exists('DocType', dt):
				rename_doc('DocType', dt, doc_rename_map[dt], force=True)

		for dn in field_rename_map:
			if frappe.db.exists('DocType', dn):
				frappe.reload_doc(get_doctype_module(dn), "doctype", scrub(dn))

		for dt, field_list in field_rename_map.items():
			if frappe.db.exists('DocType', dt):
				for field in field_list:
					if frappe.db.has_column(dt, field[0]):
						rename_field(dt, field[0], field[1])
