from __future__ import unicode_literals
import frappe

from frappe import _

def get_context(context):
	context.no_cache = 1

	task = frappe.get_doc('Task', frappe.form_dict.task)

	context.comments = frappe.db.sql("""
			select `tabCommunication`.subject, `tabCommunication`.sender_full_name, `tabCommunication`.communication_date
			from `tabCommunication`
			inner join `tabDynamic Link`
			on `tabCommunication`.name=`tabDynamic Link`.parent where
			`tabDynamic Link`.link_name='{0}' and
			`tabCommunication`.comment_type='comment'
		""".format(task.name), as_dict=True)

	context.doc = task