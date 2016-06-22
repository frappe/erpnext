# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
	columns = [
		{
			'fieldname': 'creation_date',
			'label': 'Date',
			'fieldtype': 'Date'
		},
		{
			'fieldname': 'mins',
			'fieldtype': 'Float',
			'label': 'Mins to First Response'
		},
	]

	data = frappe.db.sql('''select date(creation) as creation_date,
		avg(mins_to_first_response) as mins
		from tabOpportunity
			where date(creation) between %s and %s
			and mins_to_first_response > 0
		group by creation_date order by creation_date desc''', (filters.from_date, filters.to_date))

	return columns, data
