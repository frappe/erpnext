from __future__ import unicode_literals
import frappe

# Functions to get homepage details
@frappe.whitelist(allow_guest=True)
def get_portal_details():
	settings = frappe.get_doc("Education Settings")
	title = settings.portal_title
	description = settings.description
	return dict(title=title, description=description)

@frappe.whitelist(allow_guest=True)
def get_featured_programs():
	featured_program_names = frappe.get_all("Program", filters={"is_published": True, "is_featured": True})
	featured_list = [program["name"] for program in featured_program_names]
	if featured_list:
		return featured_list
	else:
		return None

# Functions to get program & course details
@frappe.whitelist(allow_guest=True)
def get_program_details(program_name):
	try:
		program = frappe.get_doc('Program', program_name)
		return program
	except:
		return None

@frappe.whitelist(allow_guest=True)
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

@frappe.whitelist()
def evaluate_quiz(quiz_response, quiz_name):
	"""LMS Function: Evaluates a simple multiple choice quiz.


	:param quiz_response: contains user selected choices for a quiz in the form of a string formatted as a dictionary. The function uses `json.loads()` to convert it to a python dictionary.
	"""
	import json
	quiz_response = json.loads(quiz_response)
	quiz = frappe.get_doc("Quiz", quiz_name)
	answers, score = quiz.evaluate(quiz_response, quiz_name)
	return(score)
	# quiz_name = kwargs.get('quiz')
	# course_name = kwargs.get('course')
	# enrollment = get_course_enrollment(course_name, frappe.session.user)
	# try:
	# 	quiz = frappe.get_doc("Quiz", quiz_name)
	# 	answers, score = quiz.evaluate(quiz_response, enrollment, quiz_name)
	# 	add_quiz_activity(enrollment, quiz_name, score, answers, quiz_response)
	# 	return score
	# except frappe.DoesNotExistError:
	# 	frappe.throw("Quiz {0} does not exist".format(quiz_name))
	# 	return None

@frappe.whitelist()
def get_completed_courses(email=frappe.session.user):
	try:
		print(email)
		student = frappe.get_doc("Student", get_student_id(email))
		return student.get_completed_courses()
	except:
		return None

@frappe.whitelist()
def get_continue_data(program_name):
	program = frappe.get_doc("Program", program_name)
	courses = program.get_all_children()
	continue_data = get_starting_content(courses[0].course)
	continue_data['course'] = courses[0].course
	return continue_data

def create_student(student_name=frappe.session.user):
	student = frappe.get_doc({
		"doctype": "Student",
		"first_name": student_name,
		"student_email_id": student_name,
		})
	student.save()
	frappe.db.commit()
	return student_name

@frappe.whitelist()
def enroll_all_courses_in_program(program_enrollment, student):
	course_list = [course.name for course in get_courses(program_enrollment.program)]
	for course_name in course_list:
		student.enroll_in_course(course_name=course_name, program_enrollment=program_enrollment.name)

@frappe.whitelist()
def enroll_in_program(program_name, student_email_id):
	if(not get_student_id(student_email_id)):
		create_student(student_email_id)
	student = frappe.get_doc("Student", get_student_id(student_email_id))
	program_enrollment = student.enroll_in_program(program_name)
	enroll_all_courses_in_program(program_enrollment, student)

@frappe.whitelist()
def get_student_id(email=None):
	"""Returns student user name, example EDU-STU-2018-00001 (Based on the naming series).

	:param user: a user email address
	"""
	try:
		return frappe.get_all('Student', filters={'student_email_id': email}, fields=['name'])[0].name
	except IndexError:
		return None

@frappe.whitelist()
def get_program_enrollments(email=frappe.session.user):
	try:
		student = frappe.get_doc("Student", get_student_id(email))
		return student.get_program_enrollments()
	except:
		return None

@frappe.whitelist()
def get_course_enrollments(email=frappe.session.user):
	try:
		student = frappe.get_doc("Student", get_student_id(email))
		return student.get_course_enrollments()
	except:
		return None

@frappe.whitelist()
def add_activity(enrollment, content_type, content):
	activity = frappe.get_doc({
		"doctype": "Course Activity",
		"enrollment": enrollment,
		"content_type": content_type,
		"content": content,
		"activity_date": frappe.utils.datetime.datetime.now()
		})
	activity.save()
	frappe.db.commit()