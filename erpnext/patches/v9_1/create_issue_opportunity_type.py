# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute():
	# delete custom field if exists
	for doctype, fieldname in (('Issue', 'issue_type'), ('Opportunity', 'opportunity_type')):
		custom_field = frappe.db.get_value("Custom Field", {"fieldname": fieldname, 'dt': doctype})
		if custom_field:
			frappe.delete_doc("Custom Field", custom_field, ignore_permissions=True)

	frappe.reload_doc('support', 'doctype', 'issue_type')
	frappe.reload_doc('support', 'doctype', 'issue')
	frappe.reload_doc('crm', 'doctype', 'opportunity_type')
	frappe.reload_doc('crm', 'doctype', 'opportunity')

	# rename enquiry_type -> opportunity_type
	from frappe.model.utils.rename_field import rename_field
	rename_field('Opportunity', 'enquiry_type', 'opportunity_type')

	# create values if already set
	for opts in (('Issue', 'issue_type', 'Issue Type'),
		('Opportunity', 'opportunity_type', 'Opportunity Type')):
		for d in frappe.db.sql('select distinct {0} from `tab{1}`'.format(opts[1], opts[0])):
			if d[0] and not frappe.db.exists(opts[2], d[0]):
				frappe.get_doc(dict(doctype = opts[2], name=d[0])).insert()

	# fixtures
	for name in ('Hub', _('Sales'), _('Support'), _('Maintenance')):
		if not frappe.db.exists('Opportunity Type', name):
			frappe.get_doc(dict(doctype = 'Opportunity Type', name=name)).insert()
