import frappe

FAVORITE_ARTICLE_LIMIT = 6


def get_context(context):
	context.no_cache = 1
	context.align_greeting = ""
	setting = frappe.get_doc("Support Settings")

	context.greeting_title = setting.greeting_title
	context.greeting_subtitle = setting.greeting_subtitle

	# Support content
	favorite_articles = get_favorite_articles_by_page_view()
	if len(favorite_articles) < FAVORITE_ARTICLE_LIMIT:
		name_list = []
		if favorite_articles:
			for article in favorite_articles:
				name_list.append(article.name)
		for record in frappe.get_all(
			"Help Article",
			fields=["title", "content", "route", "category"],
			filters={"name": ["not in", tuple(name_list)], "published": 1},
			order_by="creation desc",
			limit=(FAVORITE_ARTICLE_LIMIT - len(favorite_articles)),
		):
			favorite_articles.append(record)

	context.favorite_article_list = get_favorite_articles(favorite_articles)
	context.help_article_list = get_help_article_list()


def get_favorite_articles_by_page_view():
	"""Return the most-viewed published Help Articles, most viewed first."""
	# Web Page View lives in the log database, so it cannot be joined to Help Article
	published = frappe.get_all(
		"Help Article",
		fields=["name", "route"],
		filters={"published": 1, "route": ("is", "set")},
		limit=0,
	)
	if not published:
		return []

	# Lowercase keys: a case-insensitive backend may return a path in any spelling of the route
	articles_by_route = {article.route.lower(): article.name for article in published}

	counts = {}
	for row in frappe.get_all(
		"Web Page View",
		# Aliased, because the driver names an unaliased COUNT(*) differently per backend
		fields=["path", {"COUNT": "*", "as": "count"}],
		filters={"path": ("in", [article.route for article in published])},
		group_by="path",
		# Postgres rejects the default `creation desc` on a grouped query
		order_by="path",
		limit=len(published),
	):
		name = articles_by_route.get(row["path"].lower())
		if name:
			counts[name] = counts.get(name, 0) + row["count"]

	if not counts:
		return []

	# Stable sort keeps the path order for equal counts
	ranked = sorted(counts.items(), key=lambda item: -item[1])[:FAVORITE_ARTICLE_LIMIT]

	# Read `content` only for the ranked articles
	articles = {
		article.name: article
		for article in frappe.get_all(
			"Help Article",
			fields=["name", "title", "content", "route", "category"],
			filters={"name": ("in", [name for name, _ in ranked])},
			limit=len(ranked),
		)
	}

	return [frappe._dict(articles[name], count=count) for name, count in ranked if name in articles]


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
