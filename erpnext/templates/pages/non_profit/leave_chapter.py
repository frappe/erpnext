import frappe


def get_context(context):
	context.no_cache = True
	chapter = frappe.get_doc("Chapter", frappe.form_dict.name)
	context.member_deleted = True
	context.chapter = chapter
