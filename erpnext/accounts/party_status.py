# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe

from frappe.utils import evaluate_filters
from erpnext.startup.notifications import get_notification_config

status_depends_on = {
	'Customer': ('Opportunity', 'Quotation', 'Sales Order', 'Sales Invoice', 'Project', 'Issue'),
	'Supplier': ('Supplier Quotation', 'Purchase Order', 'Purchase Invoice')
}

default_status = {
	'Customer': 'Active',
	'Supplier': None
}

def notify_status(doc, method):
	'''Notify status to customer, supplier'''

	party_type = None
	for key, doctypes in status_depends_on.iteritems():
		if doc.doctype in doctypes:
			party_type = key
			break

	if not party_type:
		return

	party = frappe.get_doc(party_type, doc.get(party_type.lower()))
	config = get_notification_config().get('for_doctype').get(doc.doctype)

	status = None
	if config:
		if evaluate_filters(doc, config):
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
			update_status(party, )

def update_status(doc):
	'''Set status as open if there is any open notification'''
	config = get_notification_config()

	original_status = doc.status

	doc.status = default_status[doc.doctype]
	for doctype in status_depends_on[doc.doctype]:
		filters = config.get('for_doctype', {}).get(doctype) or {}
		filters[doc.doctype.lower()] = doc.name
		if filters:
			open_count = frappe.get_all(doctype, fields='count(*) as count', filters=filters)
			if open_count[0].count > 0:
				doc.status = 'Open'
				break

	if doc.status != original_status:
		doc.db_set('status', doc.status)
