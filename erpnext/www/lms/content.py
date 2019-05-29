from __future__ import unicode_literals
import erpnext.education.utils as utils
import frappe

no_cache = 1

def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = '/lms'
		raise frappe.Redirect

	context.course = frappe.form_dict['course']
	context.topic = frappe.form_dict['topic']
	content = frappe.form_dict['content']
	context.content_type = frappe.form_dict['type']

	context.content = frappe.get_doc(context.content_type, content).as_dict()
	context.previous = get_previous_content(context.topic, context.course, context.content, context.content_type)
	context.next = get_next_content(context.topic, context.course, context.content, context.content_type)

def get_next_content(topic, course, content, content_type):
	if frappe.session.user == "Guest":
		return None
	topic = frappe.get_doc("Topic", topic)
	content_list = [{'content_type':item.doctype, 'content':item.name} for item in topic.get_contents()]
	current_index = content_list.index({'content': content.name, 'content_type': content_type})
	try:
		return content_list[current_index + 1]
	except IndexError:
		return None

def get_previous_content(topic, course, content, content_type):
	if frappe.session.user == "Guest":
		return None
	topic = frappe.get_doc("Topic", topic)
	content_list = [{'content_type':item.doctype, 'content':item.name} for item in topic.get_contents()]
	current_index = content_list.index({'content': content.name, 'content_type': content_type})
	if current_index == 0:
		return None
	else:
		return content_list[current_index - 1]