# Copyright (c) 2020, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
	if frappe.db.exists('DocType', 'Issue') and frappe.db.count('Issue'):
		invalid_issues = frappe.get_all('Issue', {
			'first_responded_on': ['is', 'set'],
			'response_by_variance': ['<', 0]
		}, ["name", "response_by_variance", "timestampdiff(Second, `first_responded_on`, `response_by`) as variance"])

		# issues which has response_by_variance set as -ve
		# but didn't diff between first_responded_on & response_by is +ve i.e SLA isn't failed
		invalid_issues = [d for d in invalid_issues if d.get('variance') > 0]

		if not invalid_issues:
			return

		for issue in invalid_issues:
			frappe.db.set_value('Issue', issue.get('name'), 'response_by_variance', issue.get('variance'), update_modified=False)