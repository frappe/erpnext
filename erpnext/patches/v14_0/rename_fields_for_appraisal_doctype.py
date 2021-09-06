import frappe
from frappe.model.utils.rename_field import rename_field
def execute():

    if frappe.db.table_exists("Appraisal"):
        rename_field_map = {
            'total_score': 'overall_score',
            'kra_template': 'appraisal_template'
        }

        for old_name, new_name in rename_field_map.items():
            rename_field("Appraisal", old_name, new_name)

    if frappe.db.table_exists("Appraisal Template"):
        
        rename_field_map = {
            'kra_title': 'appraisal_template_title'
        }

        for old_name, new_name in rename_field_map.items():
            rename_field("Appraisal Template", old_name, new_name)
