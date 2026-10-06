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
	"""Return the most-viewed published Help Articles, most viewed first.

	The two sides of this used to be one statement joining `tabHelp Article` to
	`tabWeb Page View`. Web Page View is a virtual DocType whose rows live in the site's
	separate log database, so no single query can reach both tables -- on a fresh site the
	join raises "table doesn't exist", and on an upgraded one it silently matches nothing.

	Matching by route here instead keeps working either way: `frappe.get_all` reads whichever
	storage the DocType declares, so this is correct both on a Frappe that holds page views in
	the site database and on one that holds them in the log database.
	"""
	# route is the unique page URL, so there is one published article per route -- the same
	# assumption the previous GROUP BY route relied on.
	articles = {
		article.route: article
		for article in frappe.get_all(
			"Help Article",
			fields=["name", "title", "content", "route", "category"],
			filters={"published": 1, "route": ("is", "set")},
			limit=0,
		)
	}

	if not articles:
		return []

	routes = list(articles)
	view_counts = frappe.get_all(
		"Web Page View",
		fields=["path", {"COUNT": "*"}],
		filters={"path": ("in", routes)},
		group_by="path",
		# Ordered by the grouped column, not by the default `creation desc`: ordering a grouped
		# query by an ungrouped column is rejected on postgres, which is where these rows still
		# live on a Frappe that has not moved Web Page View to the log database.
		order_by="path",
		# An explicit limit rather than 0: older Frappe versions read 0 as the default page of
		# 20 when a DocType is virtual. One row per matching route, so this is the true bound.
		limit=len(routes),
	)

	# Ordered and trimmed here rather than in the query: a virtual DocType's controller is not
	# obliged to support ordering by an aggregate, and the row count is already bounded by the
	# number of published articles.
	view_counts.sort(key=lambda row: row["COUNT(*)"], reverse=True)

	return [
		frappe._dict(articles[row["path"]], count=row["COUNT(*)"])
		for row in view_counts[:FAVORITE_ARTICLE_LIMIT]
	]


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
