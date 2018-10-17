from __future__ import unicode_literals
import erpnext.education.utils as utils
import frappe


def get_context(context):
    if frappe.form_dict['course']:
        context.current_content = frappe.get_doc("Content", frappe.form_dict["content"])
        context.course_name = frappe.form_dict["course"]
        context.current_course = utils.get_contents_in_course(context.course_name)
        context.current_program = frappe.form_dict["program"]
        context.next_content = get_next_content(context)
        if context.current_content.content_type == "Quiz":
            context.questions = utils.get_quiz_as_dict(context.current_content.name)


def get_next_content(context):
    if context.current_course:
        course_data = [content.name for content in context.current_course]
        try:
            return course_data[course_data.index(context.current_content.name) + 1]
        except IndexError:
            return None