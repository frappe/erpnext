from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	#Rename Grading Structure to Grading Scale
	if not frappe.db.exists("DocType", "Grading Scale"):
		frappe.rename_doc("DocType", "Grading Structure", "Grading Scale", force=True)
	if not frappe.db.exists("DocType", "Grading Scale Interval"):
		frappe.rename_doc("DocType", "Grade Interval", "Grading Scale Interval", force=True)

	# frappe.reload_doc("schools", "doctype", "grading_scale_interval")
	frappe.reload_doc("education", "doctype", "grading_scale_interval")
	if "to_score" in frappe.db.get_table_columns("Grading Scale Interval"):
		rename_field("Grading Scale Interval", "to_score", "threshold")

	if not frappe.db.exists("DocType", "Assessment Plan"):
		frappe.rename_doc("DocType", "Assessment", "Assessment Plan", force=True)

	# 'Schools' module changed to the 'Education'
	# frappe.reload_doc("schools", "doctype", "assessment_plan")

	#Rename Assessment Results
	frappe.reload_doc("education", "doctype", "assessment_plan")
	if "grading_structure" in frappe.db.get_table_columns("Assessment Plan"):
		rename_field("Assessment Plan", "grading_structure", "grading_scale")

	# frappe.reload_doc("schools", "doctype", "assessment_result")
	# frappe.reload_doc("schools", "doctype", "assessment_result_detail")
	# frappe.reload_doc("schools", "doctype", "assessment_criteria")
	frappe.reload_doc("education", "doctype", "assessment_result")
	frappe.reload_doc("education", "doctype", "assessment_result_detail")
	frappe.reload_doc("education", "doctype", "assessment_criteria")


	for assessment in frappe.get_all("Assessment Plan", 
			fields=["name", "grading_scale"], filters = [["docstatus", "!=", 2 ]]):
		for stud_result in frappe.db.sql("select * from `tabAssessment Result` where parent= %s", 
				assessment.name, as_dict=True):
			if stud_result.result:
				assessment_result = frappe.new_doc("Assessment Result")
				assessment_result.student = stud_result.student
				assessment_result.student_name = stud_result.student_name
				assessment_result.assessment_plan = assessment.name
				assessment_result.grading_scale = assessment.grading_scale
				assessment_result.total_score = stud_result.result
				assessment_result.flags.ignore_validate = True
				assessment_result.flags.ignore_mandatory = True
				assessment_result.save()
	
	frappe.db.sql("""delete from `tabAssessment Result` where parent != '' or parent is not null""")