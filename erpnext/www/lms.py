from __future__ import unicode_literals
import erpnext.education.utils as utils
import frappe

# Academy Utils
@frappe.whitelist(allow_guest=True)
def get_portal_details():
	"""
	Returns portal details from Education Settings Doctype. This contains the Title and Description for LMS amoung other things.
	"""
	settings = frappe.get_doc("Education Settings")
	title = settings.portal_title
	description = settings.description
	return dict(title=title, description=description)

@frappe.whitelist(allow_guest=True)
def get_featured_programs():
	featured_program_names = frappe.get_all("Program", filters={"is_published": True, "is_featured": True})
	if featured_program_names:
		featured_list = [utils.get_program(program['name']) for program in featured_program_names]
		return featured_list
	else:
		return None

@frappe.whitelist(allow_guest=True)
def get_all_programs():
	program_names = frappe.get_all("Program", filters={"is_published": True})
	if program_names:
		featured_list = [utils.get_program(program['name']) for program in program_names]
		return featured_list
	else:
		return None

@frappe.whitelist(allow_guest=True)
def get_program_details(program_name):
	try:
		program = frappe.get_doc('Program', program_name)
		return program
	except:
		return None

# Functions to get program & course details
@frappe.whitelist(allow_guest=True)
def get_courses(program_name):
	program = frappe.get_doc('Program', program_name)
	courses = program.get_course_list()
	course_data = [{'meta':get_continue_content(item.name), 'course':item} for item in courses]
	return course_data

def get_continue_content(course_name):
	if frappe.session.user == "Guest":
		return dict(content=None, content_type=None, flag=None)
	enrollment = utils.get_course_enrollment(course_name)
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

def add_quiz_activity(enrollment, quiz_name, result_data, score, status):
	quiz_activity = frappe.get_doc({
		"doctype": "Quiz Activity",
		"enrollment": enrollment,
		"quiz": quiz_name,
		"activity_date": frappe.utils.datetime.datetime.now(),
		"result": result_data,
		"score": score,
		"status": status
		})
	quiz_activity.save()
	frappe.db.commit()

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
def enroll_in_program(program_name):
	if(not utils.get_current_student()):
		utils.create_student(frappe.session.user)
	student = frappe.get_doc("Student", utils.get_current_student())
	program_enrollment = student.enroll_in_program(program_name)
	utils.enroll_all_courses_in_program(program_enrollment, student)
	return program_name

@frappe.whitelist()
def get_program_enrollments():
	if utils.get_current_student() == None:
		return None
	try:
		student = frappe.get_doc("Student", utils.get_current_student())
		return student.get_program_enrollments()
	except:
		return None

@frappe.whitelist()
def get_all_course_enrollments():
	student = utils.get_current_student()
	if student == None:
		return None
	try:
		student = frappe.get_doc("Student", student)
		return student.get_all_course_enrollments()
	except:
		return None

# Academty Activity 
@frappe.whitelist()
def add_activity(enrollment, content_type, content):
	if(utils.check_activity_exists(enrollment, content_type, content)):
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

def get_course_progress(course_enrollment):
	course = frappe.get_doc('Course', course_enrollment.course)

	content_activity, quiz_activity = course_enrollment.get_linked_activity()
	content_list, quiz_list = course.get_contents_based_on_type()
	
	quiz_scores, is_quiz_complete, last_quiz_attempted = get_quiz_progress(quiz_list, quiz_activity)
	is_content_complete, last_content_viewed = get_content_progress(content_list, content_activity)

	quiz_data = {
		'gradable_quiz_attempts': quiz_scores,
		'complete': is_quiz_complete,
		'last': last_quiz_attempted
	}

	content_data = {
		'complete': is_content_complete,
		'last': last_content_viewed
	}
	
	return quiz_data, content_data

def get_quiz_progress(quiz_list, quiz_activity):
	scores = []
	is_complete = True
	last_attempted = None
	for quiz in quiz_list:
		attempts = [attempt for attempt in quiz_activity if attempt.quiz==quiz.name]
		if attempts and quiz.grading_basis == 'Last Attempt':
			scores.append(attempts[0])
			last_attempted = quiz
		elif attempts and quiz.grading_basis == 'Last Highest Score':
			sorted_by_score = sorted(attempts, key = lambda i: int(i.score), reverse=True)
			scores.append(sorted_by_score[0])
			last_attempted = quiz
		elif not attempts:
			is_complete = False
	return scores, is_complete, last_attempted

def get_content_progress(content_list, content_activity):
	is_complete = True
	last_viewed = None
	activity_list = [[activity.content, activity.content_type] for activity in content_activity]
	for item in content_list:
		current_content = [item.name, item.doctype]
		if current_content in activity_list:
			last_viewed = item
		else:
			is_complete = False
	return is_complete, last_viewed