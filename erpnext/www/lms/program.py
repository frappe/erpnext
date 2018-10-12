from __future__ import unicode_literals
from erpnext.education.utils import get_student_name
import frappe


def get_context(context):
    print(get_student_name(frappe.session.user))
    context.program = frappe.get_doc("Program", frappe.form_dict["program"])
    context.course_list, context.course_data = get_courses(context)

def get_courses(context):
    course_data = {}
    course_names = [program.course_name for program in context.program.courses]
    program_courses = [frappe.get_doc('Course', name) for name in course_names]
    for course_item in program_courses:
        course_data[course_item.name] = [content_item.content for content_item in course_item.course_content if content_item.content_type in ('Video', 'Article')]
    return course_names, course_data
