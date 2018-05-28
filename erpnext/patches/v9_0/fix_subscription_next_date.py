# Copyright (c) 2017, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate
from frappe.desk.doctype.auto_repeat.auto_repeat import get_next_schedule_date

def execute():
	frappe.reload_doc('accounts', 'doctype', 'subscription')
	fields = ["name", "reference_doctype", "reference_document",
			"start_date", "frequency", "repeat_on_day"]

	for d in fields:
		if not frappe.db.has_column('Subscription', d):
			return

	doctypes = ('Purchase Order', 'Sales Order', 'Purchase Invoice', 'Sales Invoice')
	for data in frappe.get_all('Subscription',
		fields = fields,
		filters = {'reference_doctype': ('in', doctypes), 'docstatus': 1}):

		recurring_id = frappe.db.get_value(data.reference_doctype, data.reference_document, "recurring_id")
		if recurring_id:
			frappe.db.sql("update `tab{0}` set subscription=%s where recurring_id=%s"
				.format(data.reference_doctype), (data.name, recurring_id))

		date_field = 'transaction_date'
		if data.reference_doctype in ['Sales Invoice', 'Purchase Invoice']:
			date_field = 'posting_date'

		start_date = frappe.db.get_value(data.reference_doctype, data.reference_document, date_field)

		if start_date and getdate(start_date) != getdate(data.start_date):
			last_ref_date = frappe.db.sql("""
				select {0}
				from `tab{1}`
				where subscription=%s and docstatus < 2
				order by creation desc
				limit 1
			""".format(date_field, data.reference_doctype), data.name)[0][0]

			next_schedule_date = get_next_schedule_date(last_ref_date, data.frequency, data.repeat_on_day)

			frappe.db.set_value("Subscription", data.name, {
				"start_date": start_date,
				"next_schedule_date": next_schedule_date
			}, None)