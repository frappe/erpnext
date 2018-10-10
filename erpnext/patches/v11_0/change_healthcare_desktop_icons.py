import frappe
from frappe import _

def execute():
	change_healthcare_desktop_icons()

def change_healthcare_desktop_icons():
	change_icons_map = [
		{
			"module_name": "Patient",
			"color": "#6BE273",
			"icon": "fa fa-user",
			"doctype": "Patient",
			"type": "link",
			"link": "List/Patient",
			"label": _("Patient")
		},
		{
			"module_name": "Patient Encounter",
			"color": "#2ecc71",
			"icon": "fa fa-stethoscope",
			"doctype": "Patient Encounter",
			"type": "link",
			"link": "List/Patient Encounter",
			"label": _("Patient Encounter"),
		},
		{
			"module_name": "Healthcare Practitioner",
			"color": "#2ecc71",
			"icon": "fa fa-user-md",
			"doctype": "Healthcare Practitioner",
			"type": "link",
			"link": "List/Healthcare Practitioner",
			"label": _("Healthcare Practitioner")
		},
		{
			"module_name": "Patient Appointment",
			"color": "#934F92",
			"icon": "fa fa-calendar-plus-o",
			"doctype": "Patient Appointment",
			"type": "link",
			"link": "List/Patient Appointment",
			"label": _("Patient Appointment")
		},
		{
			"module_name": "Lab Test",
			"color": "#7578f6",
			"icon": "octicon octicon-beaker",
			"doctype": "Lab Test",
			"type": "link",
			"link": "List/Lab Test",
			"label": _("Lab Test")
		}
	]

	for spec in change_icons_map:
		frappe.db.sql("""
			update `tabDesktop Icon`
			set module_name = '{0}', color = '{1}', icon = '{2}', _doctype = '{3}', type = '{4}',
			link = '{5}', label = '{6}'
			where _doctype = '{7}'
		""".format(spec['module_name'], spec['color'], spec['icon'], spec['doctype'], spec['type'], spec['link'], spec['label'], spec['doctype']))

	frappe.db.sql("""
		update `tabDesktop Icon`
		set color = '#FF888B', icon = 'fa fa-heartbeat'
		where module_name = 'Healthcare' and type = 'module'
	""")
