from __future__ import unicode_literals
import frappe


def get_context(context):
    context.current_course = frappe.get_doc("Course", frappe.form_dict["course"])
    context.current_content = frappe.get_doc("Content", frappe.form_dict["content"])
    next_content = get_next_content()