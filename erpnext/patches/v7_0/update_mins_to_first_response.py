from __future__ import unicode_literals
import frappe

from frappe.core.doctype.communication.email import update_mins_to_first_communication

def execute():
	frappe.reload_doctype('Issue')
	frappe.reload_doctype('Opportunity')

	for doctype in ('Issue', 'Opportunity'):
		frappe.db.sql('update tab{0} set mins_to_first_response=0'.format(doctype))
		for parent in frappe.get_all(doctype, order_by='creation desc', limit=500):
			parent_doc = frappe.get_doc(doctype, parent.name)

			for communication in frappe.db.sql("""
				select `tabCommunciation`.name from `tabCommunciation`
				inner join `tabDynamic Link`
				inner join on `tabCommunciation`.name=`tabDynamic Link`.parent where
				`tabDynamic Link`.link_doctype='{0}' and
				`tabDynamic Link`.link_name='{1}' and
				`tabCommunication`.communication_medium='Email'
				order by `tabCommunication`.creation asc
				limit 0, 2
				""".format(doctype, parent.name), as_dict=True):

				communication_doc = frappe.get_doc('Communication', communication.name)

				update_mins_to_first_communication(parent_doc, communication_doc)

				if parent_doc.mins_to_first_response:
					continue