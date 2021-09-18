# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe.utils.dashboard import cache_source
from six import iteritems

from erpnext.loan_management.report.applicant_wise_loan_security_exposure.applicant_wise_loan_security_exposure import (
	get_loan_security_details,
)


@frappe.whitelist()
@cache_source
def get_data(chart_name = None, chart = None, no_cache = None, filters = None, from_date = None,
	to_date = None, timespan = None, time_interval = None, heatmap_year = None):
	if chart_name:
		chart = frappe.get_doc('Dashboard Chart', chart_name)
	else:
		chart = frappe._dict(frappe.parse_json(chart))

	filters = {}
	current_pledges = {}

	if filters:
		filters = frappe.parse_json(filters)[0]

	conditions = ""
	labels = []
	values = []

	if filters.get('company'):
		conditions = "AND company = %(company)s"

	loan_security_details = get_loan_security_details()

	unpledges = frappe._dict(frappe.db.sql("""
		SELECT u.loan_security, sum(u.qty) as qty
		FROM `tabLoan Security Unpledge` up, `tabUnpledge` u
		WHERE u.parent = up.name
		AND up.status = 'Approved'
		{conditions}
		GROUP BY u.loan_security
	""".format(conditions=conditions), filters, as_list=1))

	pledges = frappe._dict(frappe.db.sql("""
		SELECT p.loan_security, sum(p.qty) as qty
		FROM `tabLoan Security Pledge` lp, `tabPledge`p
		WHERE p.parent = lp.name
		AND lp.status = 'Pledged'
		{conditions}
		GROUP BY p.loan_security
	""".format(conditions=conditions), filters, as_list=1))

	for security, qty in iteritems(pledges):
		current_pledges.setdefault(security, qty)
		current_pledges[security] -= unpledges.get(security, 0.0)

	sorted_pledges = dict(sorted(current_pledges.items(), key=lambda item: item[1], reverse=True))

	count = 0
	for security, qty in iteritems(sorted_pledges):
		values.append(qty * loan_security_details.get(security, {}).get('latest_price', 0))
		labels.append(security)
		count +=1

		## Just need top 10 securities
		if count == 10:
			break

	return {
		'labels': labels,
		'datasets': [{
			'name': 'Top 10 Securities',
			'chartType': 'bar',
			'values': values
		}]
	}
