from __future__ import unicode_literals
import erpnext.education.utils as utils
from urlparse import urlparse, parse_qs
import frappe


def get_context(context):
    if frappe.form_dict['course']:
        # Save form_dict variables
        program_name = frappe.form_dict["program"]
        course_name = frappe.form_dict["course"]
        content_name = frappe.form_dict["content"]
        content_type = frappe.form_dict["type"]

        # Get the required doctypes
        current_course = frappe.get_doc("Course", course_name)
        current_content = frappe.get_doc(content_type, content_name)

        # Saving context variables for Jinja
        context.content = current_content
        context.course_name = course_name
        context.program_name = program_name
        context.content_type = content_type
        context.next_content_type, context.next_content = get_next_content(content_name, content_type, current_course.get_content_info())

def get_next_content(c_name, c_type, content_list):
    try:
        next = content_list[content_list.index([c_type, c_name]) + 1]
        return next[0], next[1]
    except IndexError:
        return None, None