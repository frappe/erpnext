from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.utils.user import is_website_user
import requests

def get_context(context):
	context.no_cache = 1
	context.align_greeting = ''
	context.align_search_box = 'search-input-alignment-left'
	s = frappe.get_doc("Support Settings")

	context.greeting_text = s.greeting_text if s.greeting_text else _("We're here to help")

	if s.greeting_text_and_search_bar_alignment == 'Center':
		context.align_greeting = 'text-center'
		context.align_search_box = 'search-input-alignment-center'
	if s.greeting_text_and_search_bar_alignment == 'Right':
		context.align_greeting = 'text-end'
		context.align_search_box = 'search-input-alignment-right'
	
	# Support content
	favorite_article_count = 0
	context.favorite_article_list=[]
	context.help_article_list=[]
	context.category_list = frappe.get_all("Help Category", fields="name")
	favorite_articles = get_favorite_articles()
	
	for article in favorite_articles:
		favorite_article_dict = {}
		description = frappe.utils.strip_html(article[1])
		if len(description) > 115:
			description = description[:112] + '...'
		favorite_article_dict = {
					'title': article[0],
					'description': description,
					'route': article[2],
					'category': article[3],
				}
		context.favorite_article_list.append(favorite_article_dict)

	for category in context.category_list:
		help_aricles_per_category = {}
		help_articles = frappe.get_all("Help Article", fields="*", filters={"category": category.name}, order_by="modified desc", limit=5)
		help_aricles_per_caetgory = {
			'category': category,
			'articles': help_articles,
		}
		context.help_article_list.append(help_aricles_per_caetgory)

	# Get Started sections
	if s.get_started_sections:
		sections = json.loads(s.get_started_sections)
		context.get_started_sections = sections

	# Forum posts
	if s.show_latest_forum_posts:
		topics_data, post_params = get_forum_posts(s)
		context.post_params = post_params
		context.forum_url = s.forum_url
		context.topics = topics_data[:3]

	# Issues
	ignore_permissions = False
	if is_website_user():
		ignore_permissions = True
	if frappe.session.user != "Guest":
		context.issues = frappe.get_list("Issue", fields=["name", "status", "subject", "modified"], ignore_permissions=ignore_permissions)[:3]
	else:
		context.issues = []

def get_forum_posts(s):
	response = requests.get(s.forum_url + '/' + s.get_latest_query)
	response.raise_for_status()
	response_json = response.json()

	topics_data = {} # it will actually be an array
	key_list = s.response_key_list.split(',')
	for key in key_list:
		topics_data = response_json.get(key) if not topics_data else topics_data.get(key)

	for topic in topics_data:
		topic["link"] = s.forum_url + '/' + s.post_route_string + '/' + str(topic.get(s.post_route_key))

	post_params = {
		"title": s.post_title_key,
		"description": s.post_description_key
	}
	return topics_data, post_params

def get_favorite_articles():
	return frappe.db.sql(
			"""
			SELECT
			t1.title as title,
			t1.content as content,
			t1.route as route,
			t1.category as category,
			count(t1.route) as count 
			FROM
			`tabHelp Article` AS t1 
			INNER JOIN
			`tabWeb Page View` AS t2 
			ON t1.route = t2.path 
			GROUP BY
			route 
			ORDER BY
			count DESC
			LIMIT 3;
				""")