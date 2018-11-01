from __future__ import unicode_literals
import frappe
import erpnext.education.utils as utils

# Functions to get homepage details
@frappe.whitelist()
def get_portal_details():
	settings = frappe.get_doc("Education Settings")
	title = settings.portal_title
	description = settings.description
	return dict(title=title, description=description)

@frappe.whitelist()
def get_featured_programs():
	featured_program_names = frappe.get_list("Program", filters={"is_published": True, "is_featured": True})
	featured_list = [program["name"] for program in featured_program_names]
	if featured_list:
		return featured_list
	else:
		return None

# Functions to get program & course details
@frappe.whitelist()
def get_program_details(program_name):
	try:
		program = frappe.get_doc('Program', program_name)
		return program
	except:
		return None

@frappe.whitelist()
def get_courses(program_name):
	program = frappe.get_doc('Program', program_name)
	courses = program.get_course_list()
	return courses

@frappe.whitelist()
def get_starting_content(course_name):
	course = frappe.get_doc('Course', course_name)
	content = course.course_content[0].content
	content_type = course.course_content[0].content_type
	return dict(content=content, content_type=content_type)


# Functions to get content details
@frappe.whitelist()
def get_content(content_name, content_type):
	try:
		content = frappe.get_doc(content_type, content_name)
		return content
	except:
		frappe.throw("{0} with name {1} does not exist".format(content_type, content_name))
		return None

@frappe.whitelist()
def get_next_content(content, content_type, course):
	course_doc = frappe.get_doc("Course", course)
	content_list = [{'content_type':item.content_type, 'content':item.content} for item in course_doc.get_all_children()]
	current_index = content_list.index({'content': content, 'content_type': content_type})
	try:
		return content_list[current_index + 1]
	except IndexError:
		return None

def get_quiz_with_answers(quiz_name):
	try:
		quiz = frappe.get_doc("Quiz", quiz_name).get_questions()
		quiz_output = [{'name':question.name, 'question':question.question, 'options':[{'name': option.name, 'option':option.option, 'is_correct':option.is_correct} for option in question.options]} for question in quiz]
		return quiz_output
	except:
		frappe.throw("Quiz {0} does not exist".format(quiz_name))
		return None

@frappe.whitelist()
def get_quiz_without_answers(quiz_name):
	try:
		quiz = frappe.get_doc("Quiz", quiz_name).get_questions()
		quiz_output = [{'name':question.name, 'question':question.question, 'options':[{'name': option.name, 'option':option.option} for option in question.options]} for question in quiz]
		return quiz_output
	except:
		frappe.throw("Quiz {0} does not exist".format(quiz_name))
		return None