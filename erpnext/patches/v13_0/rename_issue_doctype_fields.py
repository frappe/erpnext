# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	if frappe.db.exists('DocType', 'Issue'):
		issues = frappe.db.get_all('Issue', fields=['name', 'response_by_variance', 'resolution_by_variance', 'mins_to_first_response'])
		frappe.reload_doc('support', 'doctype', 'issue')

		# rename fields
		rename_map = {
			'agreement_fulfilled': 'agreement_status',
			'mins_to_first_response': 'first_response_time'
		}
		for old, new in rename_map.items():
			rename_field('Issue', old, new)

		# change fieldtype to duration
		for entry in issues:
			response_by_variance = convert_to_seconds(entry.response_by_variance, 'Hours')
			resolution_by_variance = convert_to_seconds(entry.resolution_by_variance, 'Hours')
			mins_to_first_response = convert_to_seconds(entry.mins_to_first_response, 'Minutes')
			frappe.db.set_value('Issue', entry.name, {
				'response_by_variance': response_by_variance,
				'resolution_by_variance': resolution_by_variance,
				'first_response_time': mins_to_first_response
			})

	if frappe.db.exists('DocType', 'Opportunity'):
		opportunities = frappe.db.get_all('Opportunity', fields=['name', 'mins_to_first_response'])
		frappe.reload_doc('crm', 'doctype', 'opportunity')
		rename_field('Opportunity', 'mins_to_first_response', 'first_response_time')

		# change fieldtype to duration
		for entry in opportunities:
			mins_to_first_response = convert_to_seconds(entry.mins_to_first_response, 'Minutes')
			frappe.db.set_value('Issue', entry.name, 'first_response_time', mins_to_first_response)

	# renamed reports from "Minutes to First Response for Issues" to "First Response Time for Issues". Same for Opportunity
	for report in ['Minutes to First Response for Issues', 'Minutes to First Response for Opportunity']:
		if frappe.db.exists('Report', report):
			frappe.delete_doc('Report', report)


def convert_to_seconds(value, unit):
	seconds = 0
	if unit == 'Hours':
		seconds = value * 3600
	if unit == 'Minutes':
		seconds = value * 60
	return seconds
