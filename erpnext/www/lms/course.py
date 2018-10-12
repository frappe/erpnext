from __future__ import unicode_literals
import frappe


def get_context(context):
    if frappe.form_dict['course']:
        context.current_course = frappe.get_doc("Course", frappe.form_dict["course"])
        context.current_content = frappe.get_doc("Content", frappe.form_dict["content"])
        context.current_program = frappe.form_dict["program"]
        context.next_content = get_next_content(context)


def get_next_content(context):
    if context.current_course:
        course_data = [content_item.content for content_item in context.current_course.course_content]
        try: 
            return course_data[course_data.index(context.current_content.name) + 1]
        except IndexError:
            return None