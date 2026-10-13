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

	This used to be one statement joining `tabHelp Article` to `tabWeb Page View`. Web Page View
	is a virtual DocType whose rows can live in a separate log database, so no single query can
	reach both tables; the two sides are matched on route across separate reads instead.
	"""
	published = frappe.get_all(
		"Help Article",
		fields=["name", "route"],
		filters={"published": 1, "route": ("is", "set")},
		limit=0,
	)
	if not published:
		return []

	# Keyed on the folded route, while the filter below sends the routes as stored. Both halves
	# matter: a case-sensitive backend only matches the route it was given, and MariaDB -- whose
	# columns are `utf8mb4_unicode_ci` -- groups case-insensitively and answers under an
	# arbitrary spelling from the group, which need not be the one the route was stored with.
	articles_by_route = {article.route.lower(): article.name for article in published}

	counts = {}
	for row in frappe.get_all(
		"Web Page View",
		# COUNT(*) is aliased because an unaliased one is named by the driver: `COUNT(*)` on
		# MariaDB and SQLite, `count` on postgres.
		fields=["path", {"COUNT": "*", "as": "count"}],
		filters={"path": ("in", [article.route for article in published])},
		group_by="path",
		# The grouped column, not the default `creation desc`: postgres rejects ordering a grouped
		# query by an ungrouped one. Ranking happens below, on the totals.
		order_by="path",
		limit=len(published),
	):
		name = articles_by_route.get(row["path"].lower())
		if name:
			counts[name] = counts.get(name, 0) + row["count"]

	if not counts:
		return []

	# `sorted` is stable and the rows arrived ordered by path, so equal counts keep a fixed order.
	ranked = sorted(counts.items(), key=lambda item: -item[1])[:FAVORITE_ARTICLE_LIMIT]

	# The only read of `content`, and only for the articles that survived the ranking: ranking in
	# python previously meant reading every published article's body to then discard all but six.
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
