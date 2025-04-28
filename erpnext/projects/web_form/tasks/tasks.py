<<<<<<< HEAD
import urllib.parse

=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
import frappe


def get_context(context):
<<<<<<< HEAD
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
=======
	if frappe.form_dict.project:
		context.parents = [
			{"title": frappe.form_dict.project, "route": "/projects?project=" + frappe.form_dict.project}
		]
		context.success_url = "/projects?project=" + frappe.form_dict.project

	elif context.doc and context.doc.get("project"):
		context.parents = [
			{"title": context.doc.project, "route": "/projects?project=" + context.doc.project}
		]
		context.success_url = "/projects?project=" + context.doc.project
>>>>>>> 7c4cf3e834 (Favicon.svg)
