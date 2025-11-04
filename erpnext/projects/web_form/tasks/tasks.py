import urllib.parse

import frappe


def get_context(context):
	if project := frappe.form_dict.project:
		title = frappe.utils.data.escape_html(project)
		route = "/projects?" + urllib.parse.urlencode({"project": project})
		context.parents = [{"title": title, "route": route}]
		context.success_url = route

	elif context.doc and (project := context.doc.get("project")):
		title = frappe.utils.data.escape_html(project)
		route = "/projects?" + urllib.parse.urlencode({"project": project})
		context.parents = [{"title": title, "route": route}]
		context.success_url = route
