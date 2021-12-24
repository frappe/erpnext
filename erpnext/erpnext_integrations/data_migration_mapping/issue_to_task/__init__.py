from __future__ import unicode_literals

import frappe


def pre_process(issue):

	project = frappe.db.get_value('Project', filters={'project_name': issue.milestone})
	return {
		'title': issue.title,
		'body': frappe.utils.md_to_html(issue.body or ''),
		'state': issue.state.title(),
		'project': project or ''
	}
