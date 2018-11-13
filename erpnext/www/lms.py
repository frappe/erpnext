from __future__ import unicode_literals
import frappe

# Academy Utils
@frappe.whitelist(allow_guest=True)
def get_portal_details():
	settings = frappe.get_doc("Education Settings")
	title = settings.portal_title
	description = settings.description
	return dict(title=title, description=description)

def check_program_enrollment(program_name):
	if frappe.session.user in ("Guest", "Administrator"):
		return False
	student = get_student_id(frappe.session.user)
	enrollment = frappe.get_list("Program Enrollment", filters={'student':student, 'program': program_name})
	if enrollment:
		return True
	else:
		return False

@frappe.whitelist(allow_guest=True)
def get_featured_programs():
	featured_program_names = frappe.get_all("Program", filters={"is_published": True, "is_featured": True})
	if featured_program_names:
		featured_list = [get_program(program['name']) for program in featured_program_names]
		return featured_list
	else:
		return None

def get_program(program_name):
	program = frappe.get_doc('Program', program_name)
	is_enrolled = check_program_enrollment(program_name)
	return {'program': program, 'is_enrolled': is_enrolled}

@frappe.whitelist(allow_guest=True)
def get_program_details(program_name):
	try:
		program = frappe.get_doc('Program', program_name)
		return program
	except:
		return None


def get_enrollment(course_name):
	student = get_student_id(frappe.session.user)
	enrollment_name = frappe.get_all("Course Enrollment", filters={'student': student, 'course':course_name})
	try:
		name = enrollment_name[0].name
		enrollment = frappe.get_doc("Course Enrollment", name)
		return enrollment
	except:
		return None

@frappe.whitelist()
def get_student_id(email=None):
	"""Returns student user name, example EDU-STU-2018-00001 (Based on the naming series).

	:param user: a user email address
	"""
	try:
		student_id = frappe.db.get_all("Student", {"student_email_id": email}, ["name"])[0].name
		return student_id
	except IndexError:
		return None

def create_student():
	student_name=frappe.session.user
	student = frappe.get_doc({
		"doctype": "Student",
		"first_name": student_name,
		"student_email_id": student_name,
		})
	student.save(ignore_permissions=True)
	frappe.db.commit()
	return student_name

# Functions to get program & course details
@frappe.whitelist(allow_guest=True)
def get_courses(program_name):
	program = frappe.get_doc('Program', program_name)
	courses = program.get_course_list()
	course_data = [{'meta':get_continue_content(item.name), 'course':item} for item in courses]
	return course_data

@frappe.whitelist()
def get_continue_content(course_name):
	if frappe.session.user == "Guest":
		return dict(content=None, content_type=None, flag=None)
	enrollment = get_enrollment(course_name)
	course = frappe.get_doc("Course", enrollment.course)
	last_activity = enrollment.get_last_activity()
	
	if last_activity == None:
		next_content = course.get_first_content()
		return dict(content=next_content.name, content_type=next_content.doctype, flag="Start")
	
	if last_activity.doctype == "Quiz Activity":
		next_content = get_next_content(last_activity.quiz, "Quiz", course.name)
	else:
		next_content = get_next_content(last_activity.content, last_activity.content_type, course.name)
	
	if next_content == None:
		next_content = course.get_first_content()
		return dict(content=next_content.name, content_type=next_content.doctype, flag="Complete")
	else:
		next_content['flag'] = "Continue"
		return next_content


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
	if frappe.session.user == "Guest":
		return None
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
def evaluate_quiz(enrollment, quiz_response, quiz_name):
	"""LMS Function: Evaluates a simple multiple choice quiz.


	:param quiz_response: contains user selected choices for a quiz in the form of a string formatted as a dictionary. The function uses `json.loads()` to convert it to a python dictionary.
	"""
	import json
	quiz_response = json.loads(quiz_response)
	quiz = frappe.get_doc("Quiz", quiz_name)
	answers, score, status = quiz.evaluate(quiz_response, quiz_name)

	result = {k: ('Correct' if v else 'Wrong') for k,v in answers.items()}
	result_data = []
	for key in answers:
		item = {}
		item['question'] = key
		item['quiz_result'] = result[key]
		try:
			item['selected_option'] = frappe.get_value('Options', quiz_response[key], 'option')
		except:
			item['selected_option'] = "Unattempted"
		result_data.append(item)
	# result_data = [{'question': key, 'selected_option': frappe.get_value('Options', quiz_response[key], 'option'), 'quiz_result': result[key]} for key in answers]

	add_quiz_activity(enrollment, quiz_name, result_data, score, status)
	return(score)

@frappe.whitelist()
def get_completed_courses():
	student = get_student_id(frappe.session.user)
	if student == None:
		return None
	try:
		student = frappe.get_doc("Student", student)
		return student.get_completed_courses()
	except:
		return None

@frappe.whitelist()
def get_continue_data(program_name):
	program = frappe.get_doc("Program", program_name)
	courses = program.get_all_children()
	try:
		continue_data = get_starting_content(courses[0].course)
		continue_data['course'] = courses[0].course
		return continue_data
	except:
		return None

@frappe.whitelist()
def enroll_all_courses_in_program(program_enrollment, student):
	program = frappe.get_doc("Program", program_enrollment.program)
	course_list = [course.course for course in program.get_all_children()]
	for course_name in course_list:
		student.enroll_in_course(course_name=course_name, program_enrollment=program_enrollment.name)

@frappe.whitelist()
def enroll_in_program(program_name):
	if(not get_student_id(frappe.session.user)):
		create_student(frappe.session.user)
	student = frappe.get_doc("Student", get_student_id(frappe.session.user))
	program_enrollment = student.enroll_in_program(program_name)
	enroll_all_courses_in_program(program_enrollment, student)

@frappe.whitelist()
def get_program_enrollments(email=frappe.session.user):
	if get_student_id(email) == None:
		return None
	try:
		student = frappe.get_doc("Student", get_student_id(email))
		return student.get_program_enrollments()
	except:
		return None

@frappe.whitelist()
def get_course_enrollments():
	student = get_student_id(frappe.session.user)
	if student == None:
		return None
	try:
		student = frappe.get_doc("Student", student)
		return student.get_course_enrollments()
	except:
		return None


# Academty Activity 
@frappe.whitelist()
def add_activity(enrollment, content_type, content):
	if(check_activity_exists(enrollment, content_type, content)):
		pass
	else:
		activity = frappe.get_doc({
			"doctype": "Course Activity",
			"enrollment": enrollment,
			"content_type": content_type,
			"content": content,
			"activity_date": frappe.utils.datetime.datetime.now()
			})
		activity.save()
		frappe.db.commit()

def check_activity_exists(enrollment, content_type, content):
	activity = frappe.get_all("Course Activity", filters={'enrollment': enrollment, 'content_type': content_type, 'content': content})
	return bool(activity)

def add_quiz_activity(enrollment, quiz_name, result_data, score, status):
	quiz_activity = frappe.get_doc({
		"doctype": "Quiz Activity",
		"enrollment": enrollment,
		"quiz": quiz_name,
		"result": result_data,
		"score": score,
		"status": status
		})
	quiz_activity.save()
	frappe.db.commit()

@frappe.whitelist()
def mark_course_complete(enrollment):
	course_enrollment = frappe.get_doc("Course Enrollment", enrollment)
	course_enrollment.completed = True
	course_enrollment.save()
	frappe.db.commit()
