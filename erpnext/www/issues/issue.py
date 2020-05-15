from __future__ import unicode_literals
import frappe


from frappe.website.utils import get_comment_list

def get_context(context):
    context.com_list = []
    issue_name = frappe.form_dict['issue']
    context.item = frappe.get_doc("Issue", issue_name)
    context.reference_doctype = "Issue"
    context.reference_name = issue_name
    context.comment_list = get_comment_list(context.reference_doctype,
					context.reference_name, reverse=False, fetch_all=True)