# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

from frappe.utils import evaluate_filters
from frappe.desk.notifications import get_filters_for

# NOTE: if you change this also update triggers in erpnext/hooks.py
status_depends_on = {
	'Customer': ('Opportunity', 'Quotation', 'Sales Order', 'Delivery Note', 'Sales Invoice', 'Project', 'Issue'),
	'Supplier': ('Supplier Quotation', 'Purchase Order', 'Purchase Receipt', 'Purchase Invoice')
}

default_status = {
	'Customer': 'Active',
	'Supplier': None
}

def notify_status(doc, method=None):
	'''Notify status to customer, supplier'''

	party_type = None
	for key, doctypes in status_depends_on.iteritems():
		if doc.doctype in doctypes:
			party_type = key
			break

	if not party_type:
		return

	name = doc.get(party_type.lower())
	if not name:
		return

	party = frappe.get_doc(party_type, name)
	filters = get_filters_for(doc.doctype)
	party.flags.ignore_mandatory = True

	status = None
	if filters:
		if evaluate_filters(doc, filters):
			# filters match, passed document is open
			status = 'Open'

	if status=='Open':
		if party.status != 'Open':
			# party not open, make it open
			party.status = 'Open'
			party.save(ignore_permissions=True)

	else:
		if party.status == 'Open':
			# may be open elsewhere, check
			# default status
			party.status = status
			update_status(party)

	party.update_modified()
	party.notify_update()

def get_party_status(doc):
	'''return party status based on open documents'''
	status = default_status[doc.doctype]
	for doctype in status_depends_on[doc.doctype]:
		filters = get_filters_for(doctype)
		filters[doc.doctype.lower()] = doc.name
		if filters:
			open_count = frappe.get_all(doctype, fields='name', filters=filters, limit_page_length=1)
			if len(open_count) > 0:
				status = 'Open'
				break

	return status

def update_status(doc):
	'''Set status as open if there is any open notification'''
	status = get_party_status(doc)
	if doc.status != status:
		doc.db_set('status', status)
