import json

import frappe
import requests


def get_context(context):
	context.no_cache = 1
	settings = frappe.get_doc("Support Settings", "Support Settings")
	s = settings

	# Get Started sections
	sections = json.loads(s.get_started_sections)
	context.get_started_sections = sections

	# Forum posts
	topics_data, post_params = get_forum_posts(s)
	context.post_params = post_params
	context.forum_url = s.forum_url
	context.topics = topics_data[:3]

	# Issues
	if frappe.session.user != "Guest":
		context.issues = frappe.get_list("Issue", fields=["name", "status", "subject", "modified"])[:3]
	else:
		context.issues = []


def get_forum_posts(s):
	response = requests.get(s.forum_url + "/" + s.get_latest_query)
	response.raise_for_status()
	response_json = response.json()

	topics_data = {}  # it will actually be an array
	key_list = s.response_key_list.split(",")
	for key in key_list:
		topics_data = response_json.get(key) if not topics_data else topics_data.get(key)

	for topic in topics_data:
		topic["link"] = s.forum_url + "/" + s.post_route_string + "/" + str(topic.get(s.post_route_key))

	post_params = {"title": s.post_title_key, "description": s.post_description_key}
	return topics_data, post_params
