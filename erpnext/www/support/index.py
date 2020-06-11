from __future__ import unicode_literals
import frappe, json
from frappe import _

def get_context(context):
	context.no_cache = 1
	context.align_greeting = ''
	setting = frappe.get_doc("Support Settings")

	context.greeting_title = setting.greeting_title
	context.greeting_subtitle = setting.greeting_subtitle
	
	# Support content
	context.favorite_article_list=[]
	context.help_article_list=[]
	context.category_list = frappe.get_all("Help Category", fields="name")
	favorite_articles = get_favorite_articles_by_page_view()
	if not favorite_articles or len(favorite_articles) < 3:
		favorite_articles = get_latest_articles()
	
	set_favorite_articles(context, favorite_articles)

	set_help_article_list(context)

def get_favorite_articles_by_page_view():
	return frappe.db.sql(
			"""
			SELECT
				t1.title as title,
				t1.content as content,
				t1.route as route,
				t1.category as category,
				count(t1.route) as count 
			FROM `tabHelp Article` AS t1 
				INNER JOIN
				`tabWeb Page View` AS t2 
			ON t1.route = t2.path 
			WHERE t1.published = 1
			GROUP BY route 
			ORDER BY count DESC
			LIMIT 6;
			""", as_dict=True)

def get_latest_articles():
	return frappe.db.sql(
		"""
		SELECT 
			title,
			content,
			route,
			category
		FROM `tabHelp Article`
		WHERE published=1
		ORDER BY creation DESC
		LIMIT 6;
		""", as_dict=True)

def set_favorite_articles(context, favorite_articles):
	for article in favorite_articles:
		description = frappe.utils.strip_html(article.content)
		if len(description) > 150:
			description = description[:150] + '...'
		favorite_article_dict = {
					'title': article.title,
					'description': description,
					'route': article.route,
					'category': article.category,
				}
		context.favorite_article_list.append(favorite_article_dict)

def set_help_article_list(context):
	for category in context.category_list:
		help_articles = frappe.get_all("Help Article", fields="*", filters={"category": category.name}, order_by="modified desc", limit=5)
		help_aricles_per_caetgory = {
			'category': category,
			'articles': help_articles,
		}
		context.help_article_list.append(help_aricles_per_caetgory)