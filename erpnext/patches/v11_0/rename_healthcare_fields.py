import frappe
from frappe.model.utils.rename_field import rename_field
from frappe.modules import scrub, get_doctype_module

lab_test_name = ["test_name", "lab_test_name"]
lab_test_code = ["test_code", "lab_test_code"]
lab_test_comment = ["test_comment", "lab_test_comment"]
lab_test_created = ["test_created", "lab_test_created"]
lab_test_template = ["test_template", "lab_test_template"]
lab_test_rate = ["test_rate", "lab_test_rate"]
lab_test_description = ["test_description", "lab_test_description"]
lab_test_group = ["test_group", "lab_test_group"]
lab_test_template_type = ["test_template_type", "lab_test_template_type"]
lab_test_uom = ["test_uom", "lab_test_uom"]
lab_test_normal_range = ["test_normal_range", "lab_test_normal_range"]
lab_test_event = ["test_event", "lab_test_event"]
lab_test_particulars = ["test_particulars", "lab_test_particulars"]

field_rename_map = {
	"Lab Test Template": [lab_test_name, lab_test_code, lab_test_rate, lab_test_description,
		lab_test_group, lab_test_template_type, lab_test_uom, lab_test_normal_range],
	"Normal Test Items": [lab_test_name, lab_test_comment, lab_test_uom, lab_test_event],
	"Lab Test": [lab_test_name, lab_test_comment, lab_test_group],
	"Lab Prescription": [lab_test_name, lab_test_code, lab_test_comment, lab_test_created],
	"Lab Test Groups": [lab_test_template, lab_test_rate, lab_test_description],
	"Lab Test UOM": [lab_test_uom],
	"Normal Test Template": [lab_test_uom, lab_test_event],
	"Special Test Items": [lab_test_particulars]
}


def execute():
	for dt, field_list in field_rename_map.items():
		if frappe.db.exists('DocType', dt):
			frappe.reload_doc(get_doctype_module(dt), "doctype", scrub(dt))
			for field in field_list:
				if frappe.db.has_column(dt, field[0]):
					rename_field(dt, field[0], field[1])

	if frappe.db.exists('DocType', 'Lab Prescription'):
		if frappe.db.has_column('Lab Prescription', 'parentfield'):
			frappe.db.sql("""
				update `tabLab Prescription` set parentfield = 'lab_test_prescription'
				where parentfield = 'test_prescription'
			""")

	if frappe.db.exists('DocType', 'Lab Test Groups'):
		if frappe.db.has_column('Lab Test Groups', 'parentfield'):
			frappe.db.sql("""
				update `tabLab Test Groups` set parentfield = 'lab_test_groups'
				where parentfield = 'test_groups'
			""")
