from __future__ import unicode_literals
import erpnext.education.utils as utils
import frappe

no_cache = 1

def get_context(context):
	try:
		course = frappe.form_dict['course']
		program = frappe.form_dict['program']
		topic = frappe.form_dict['topic']
	except KeyError:
		frappe.local.flags.redirect_location = '/lms'
		raise frappe.Redirect

	context.program = program
	context.course = course
	context.topic = frappe.get_doc("Topic", topic)
	context.contents = get_contents(context.topic, course, program)
	context.has_access =  utils.allowed_program_access(program)

def get_contents(topic, course, program):
	student = utils.get_current_student()
	if student:
		course_enrollment = utils.get_or_create_course_enrollment(course, program)
	contents = topic.get_contents()
	progress = []
	if contents:
		for content in contents:
			if content.doctype in ('Article', 'Video'):
				if student:
					status = utils.check_content_completion(content.name, content.doctype, course_enrollment.name)
				else:
					status = True
				progress.append({'content': content, 'content_type': content.doctype, 'completed': status})
			elif content.doctype == 'Quiz':
				if student:
					status, score, result = utils.check_quiz_completion(content, course_enrollment.name)
				else:
					status = False
					score = None
					result = None
				progress.append({'content': content, 'content_type': content.doctype, 'completed': status, 'score': score, 'result': result})

	return progress