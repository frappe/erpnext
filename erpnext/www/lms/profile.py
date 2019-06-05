from __future__ import unicode_literals
import erpnext.education.utils as utils
import frappe

no_cache = 1

def get_context(context):
	context.student = utils.get_current_student()
	context.progress = get_program_progress(context.student.name)

def get_program_progress(student):
	enrolled_programs = frappe.get_all("Program Enrollment", filters={'student':student}, fields=['program'])
	student_progress = []
	for list_item in enrolled_programs:
		program = frappe.get_doc("Program", list_item.program)
		progress = utils.get_program_progress(program)
		completion = utils.get_program_completion(program)
		student_progress.append({'program': program.program_name, 'name': program.name, 'progress':progress, 'completion': completion})

	return student_progress




