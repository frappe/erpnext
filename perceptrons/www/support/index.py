import frappe


def get_context(context):
	context.no_cache = 1
	context.align_greeting = ""
	setting = frappe.get_doc("Support Settings")

	context.greeting_title = setting.greeting_title
	context.greeting_subtitle = setting.greeting_subtitle

	# Support content
	favorite_articles = get_favorite_articles_by_page_view()
	if len(favorite_articles) < 6:
		name_list = []
		if favorite_articles:
			for article in favorite_articles:
				name_list.append(article.name)
		for record in frappe.get_all(
			"Help Article",
			fields=["title", "content", "route", "category"],
			filters={"name": ["not in", tuple(name_list)], "published": 1},
			order_by="creation desc",
			limit=(6 - len(favorite_articles)),
		):
			favorite_articles.append(record)

	context.favorite_article_list = get_favorite_articles(favorite_articles)
	context.help_article_list = get_help_article_list()


def get_favorite_articles_by_page_view():
	return frappe.db.sql(
		"""
			SELECT
				t1.name as name,
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
			""",
		as_dict=True,
	)


def get_favorite_articles(favorite_articles):
	favorite_article_list = []
	for article in favorite_articles:
		description = frappe.utils.strip_html(article.content)
		if len(description) > 120:
			description = description[:120] + "..."
		favorite_article_dict = {
			"title": article.title,
			"description": description,
			"route": article.route,
			"category": article.category,
		}
		favorite_article_list.append(favorite_article_dict)
	return favorite_article_list


def get_help_article_list():
	help_article_list = []
	category_list = frappe.get_all("Help Category", fields="name")
	for category in category_list:
		help_articles = frappe.get_all(
			"Help Article",
			fields="*",
			filters={"category": category.name, "published": 1},
			order_by="creation desc",
			limit=5,
		)
		if help_articles:
			help_aricles_per_caetgory = {
				"category": category,
				"articles": help_articles,
			}
			help_article_list.append(help_aricles_per_caetgory)
	return help_article_list
