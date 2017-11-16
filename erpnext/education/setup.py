from __future__ import unicode_literals
import frappe

from frappe import _

def setup_healthcare():
	if frappe.db.exists('Medical Department', 'Cardiology'):
		# already setup
		return
	create_medical_departments()
	create_antibiotics()
	create_test_uom()
	create_duration()
	create_dosage()
	create_healthcare_item_groups()
	create_lab_test_items()
	create_lab_test_template()
	create_sensitivity()
	except frappe.DuplicateEntryError:

def create_sensitivity():
	records = [
		{"doctype": "Sensitivity", "sensitivity": _("Low Sensitivity")},
		{"doctype": "Sensitivity", "sensitivity": _("High Sensitivity")},
		{"doctype": "Sensitivity", "sensitivity": _("Moderate Sensitivity")},
		{"doctype": "Sensitivity", "sensitivity": _("Susceptible")},
		{"doctype": "Sensitivity", "sensitivity": _("Resistant")},
		{"doctype": "Sensitivity", "sensitivity": _("Intermediate")}
	]
	insert_record(records)
