from __future__ import unicode_literals
import erpnext.education.utils as utils
import frappe

no_cache = 1

def get_context(context):
	program = frappe.form_dict['program']
	content = frappe.form_dict['content']
	content_type = frappe.form_dict['type']

	has_program_access = utils.allowed_program_access(program)
	has_content_access = allowed_content_access(program, content, content_type)

	if frappe.session.user == "Guest" or not has_program_access or not has_content_access:
		frappe.local.flags.redirect_location = '/lms'
		raise frappe.Redirect

	context.content = frappe.get_doc(content_type, content).as_dict()
	context.content_type = content_type

	context.course = frappe.form_dict['course']
	context.topic = frappe.form_dict['topic']

	context.previous = get_previous_content(context.topic, context.course, context.content, context.content_type)
	context.next = get_next_content(context.topic, context.course, context.content, context.content_type)


def get_next_content(topic, course, content, content_type):
	if frappe.session.user == "Guest":
		return None
	topic = frappe.get_doc("Topic", topic)
	content_list = [{'content_type':item.doctype, 'content':item.name} for item in topic.get_contents()]
	current_index = content_list.index({'content': content.name, 'content_type': content_type})
	try:
		return content_list[current_index + 1]
	except IndexError:
		return None

def get_previous_content(topic, course, content, content_type):
	if frappe.session.user == "Guest":
		return None
	topic = frappe.get_doc("Topic", topic)
	content_list = [{'content_type':item.doctype, 'content':item.name} for item in topic.get_contents()]
	current_index = content_list.index({'content': content.name, 'content_type': content_type})
	if current_index == 0:
		return None
	else:
		return content_list[current_index - 1]

def allowed_content_access(program, content, content_type):
	# Get all content in program

	# Using ORM
	# course_in_program = [course.course for course in frappe.get_all('Program Course', fields=['course'], filters={'parent': program})]
	# topics_in_course = [topic.topic for topic in frappe.get_all("Course Topic", fields=['topic'], filters=[['parent','in', course_in_program]])]
	# contents_of_program = [[c.content, c.content_type] for c in frappe.get_all('Topic Content', fields=['content', 'content_type'], filters=[['parent','in', topics_in_course]])]

	contents_of_program = frappe.db.sql("""select `tabtopic content`.content, `tabtopic content`.content_type
	from `tabcourse topic`,
		 `tabprogram course`,
		 `tabtopic content`
	where `tabcourse topic`.parent = `tabprogram course`.course
			and `tabtopic content`.parent = `tabcourse topic`.topic
			and `tabprogram course`.parent = '{0}'""".format(program))

	return (content, content_type) in contents_of_program