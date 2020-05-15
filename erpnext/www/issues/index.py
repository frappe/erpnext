from __future__ import unicode_literals
import frappe

from erpnext.support.doctype.issue.issue import get_issue_list
from frappe.utils.user import is_website_user

def get_context(context):
	user = frappe.session.user
	context.doc_list=[]
	for issue in frappe.get_list("Issue", fields="*", filters={"owner": user}, ignore_permissions = True):
		doc = frappe.get_doc("Issue", issue.name)
		context.doc_list.append(doc)