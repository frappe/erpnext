# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	if not filters:
		filters = {}

	columns = get_columns(filters)
	data = get_data(filters)
	chart = get_chart_data(data)

	return columns, data, None, chart

def get_columns(filters=None):
	return [
		{
			'label': _('Program'),
			'fieldname': 'program',
			'fieldtype': 'Link',
			'options': 'Program',
			'width': 300
		},
		{
			'label': _('Fees Collected'),
			'fieldname': 'fees_collected',
			'fieldtype': 'Currency',
			'width': 200
		},
		{
			'label': _('Outstanding Amount'),
			'fieldname': 'outstanding_amount',
			'fieldtype': 'Currency',
			'width': 200
		},
		{
			'label': _('Grand Total'),
			'fieldname': 'grand_total',
			'fieldtype': 'Currency',
			'width': 200
		}
	]


def get_data(filters=None):
	data = []

	conditions = get_filter_conditions(filters)

	fee_details = frappe.db.sql(
		"""
			SELECT
				FeesCollected.program,
				FeesCollected.paid_amount,
				FeesCollected.outstanding_amount,
				FeesCollected.grand_total
			FROM (
				SELECT
					sum(grand_total) - sum(outstanding_amount) AS paid_amount, program,
					sum(outstanding_amount) AS outstanding_amount,
					sum(grand_total) AS grand_total
				FROM `tabFees`
				WHERE
					docstatus = 1 and
					program IS NOT NULL
					%s
				GROUP BY program
			) AS FeesCollected
			ORDER BY FeesCollected.paid_amount DESC
		""" % (conditions)
	, as_dict=1)

	for entry in fee_details:
		data.append({
			'program': entry.program,
			'fees_collected': entry.paid_amount,
			'outstanding_amount': entry.outstanding_amount,
			'grand_total': entry.grand_total
		})

	return data

def get_filter_conditions(filters):
	conditions = ''

	if filters.get('from_date') and filters.get('to_date'):
		conditions += " and posting_date BETWEEN '%s' and '%s'" % (filters.get('from_date'), filters.get('to_date'))

	return conditions


def get_chart_data(data):
	if not data:
		return

	labels = []
	fees_collected = []
	outstanding_amount = []

	for entry in data:
		labels.append(entry.get('program'))
		fees_collected.append(entry.get('fees_collected'))
		outstanding_amount.append(entry.get('outstanding_amount'))

	return {
		'data': {
			'labels': labels,
			'datasets': [
				{
					'name': _('Fees Collected'),
					'values': fees_collected
				},
				{
					'name': _('Outstanding Amt'),
					'values': outstanding_amount
				}
			]
		},
		'type': 'bar'
	}

