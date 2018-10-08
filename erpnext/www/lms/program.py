from __future__ import unicode_literals
import frappe


# Get the classroom's route parameter from the url
url_param = frappe.form_dict["code"]
# Get classroom from classroom_name
current_program = frappe.get_doc("Program", url_param)

def get_context(context):
    context.program = current_program
    context.course_list, context.course_data = get_courses()

def get_courses():
    course_data = {}
    course_names = [program.course_name for program in current_program.courses]
    program_courses = [frappe.get_doc('Course', name) for name in course_names]
    for course_item in program_courses:
        course_data[course_item.name] = [content_item.content for content_item in course_item.course_content if content_item.content_type in ('Video', 'Article')]
    return course_names, course_data
