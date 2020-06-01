from __future__ import unicode_literals
import frappe

from frappe.website.utils import get_comment_list

def get_context(context):
    context.item=[]
    issue_name = frappe.form_dict['issue']
    doc = frappe.get_all("Issue", fields="*", filters={"name": issue_name})
    subject = doc[0].subject
    if len(subject) > 50:
        subject = subject[:47] + '...'
    context.reference_doctype = "Issue"
    context.reference_name = issue_name
    context.comment_list = get_comment_list(context.reference_doctype,
					context.reference_name, reverse=False, fetch_all_comment=True, fetch_all_communication=True)
    doc = {
			'item': doc,
			'subject': subject
		}
    context.item.append(doc)