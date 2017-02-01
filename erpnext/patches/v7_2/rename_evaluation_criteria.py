import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
    frappe.rename_doc("DocType", "Evaluation Criteria", "Assessment Criteria", force=True)
    frappe.reload_doc("schools", "doctype", "assessment_criteria")
    rename_field("Assessment Criteria", "evaluation_criteria", "assessment_criteria")

    frappe.rename_doc("DocType", "Assessment Evaluation Criteria", "Assessment Plan Criteria", force=True)
    frappe.reload_doc("schools", "doctype", "assessment_plan_criteria")
    rename_field("Assessment Plan Criteria", "evaluation_criteria", "assessment_criteria")

    frappe.reload_doc("schools", "doctype", "assessment_plan")
    rename_field("Assessment Plan", "evaluation_criterias", "assessment_criteria")
        
    frappe.reload_doc("schools", "doctype", "assessment_result_detail")
    rename_field("Assessment Result Detail", "evaluation_criteria", "assessment_criteria")

    frappe.rename_doc("DocType", "Course Evaluation Criteria", "Course Assessment Criteria", force=True)
    frappe.reload_doc("schools", "doctype", "course_assessment_criteria")
    rename_field("Course Assessment Criteria", "evaluation_criteria", "assessment_criteria")

    frappe.reload_doc("schools", "doctype", "course")
    rename_field("Course", "evaluation_criterias", "assessment_criteria")
