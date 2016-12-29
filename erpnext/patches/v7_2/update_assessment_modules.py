import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	#Rename Grading Structure to Grading Scale
	frappe.rename_doc("DocType", "Grading Structure", "Grading Scale", force=True)
	frappe.rename_doc("DocType", "Grade Interval", "Grading Scale Interval", force=True)

	frappe.reload_doc("schools", "doctype", "grading_scale_interval")
	rename_field("Grading Scale Interval", "to_score", "min_score")

	#Rename Assessment Results
	frappe.reload_doc("schools", "doctype", "assessment")
	rename_field("Assessment", "grading_structure", "grading_scale")

	frappe.reload_doc("schools", "doctype", "assessment_result")
	for assessment in frappe.get_all("Assessment", fields=["name", "grading_scale"]):
		for stud_result in frappe.db.sql("select * from `tabAssessment Result` where parent= %s", assessment.name, as_dict=True):
			if stud_result.result:
				assessment_result = frappe.new_doc("Assessment Result")
				assessment_result.student = stud_result.student
				assessment_result.student_name = stud_result.student_name
				assessment_result.assessment = assessment.name
				assessment_result.grading_scale = assessment.grading_scale
				assessment_result.total_score = stud_result.result
				assessment_result.flags.ignore_validate = True
				assessment_result.save()
	
	frappe.db.sql("""delete from `tabAssessment Result` where parent != '' or parent is not null""")