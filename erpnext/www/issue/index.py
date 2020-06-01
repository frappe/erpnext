from __future__ import unicode_literals
import frappe

from erpnext.support.doctype.issue.issue import get_issue_list
from frappe.utils.user import is_website_user
from frappe.website.utils import get_comment_list

def get_context(context):
	user = frappe.session.user
	context.doc_list=[]
	for issue in frappe.get_list("Issue", fields="*", filters={"owner": user}, ignore_permissions = True):
		doc = {}
		# item = frappe.get_doc("Issue", issue.name)
		item = frappe.get_all("Issue", fields="*", filters={"name": issue.name})
		communication_list = get_comment_list("Issue",
					issue.name, reverse=False, fetch_all_comment=True, fetch_all_communication=True)
		# print(item)
		creation = item[0].creation.strftime("%d %B, %Y")
		subject = item[0].subject
		if len(subject) > 50:
			subject = subject[:47] + '...'
		# print(creation)
		print(subject)
		doc = {
			'item': item,
			'communication_count': len(communication_list),
			'created_on': creation,
			'subject': subject
		}
		context.doc_list.append(doc)