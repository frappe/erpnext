# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import random_string

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.www.support.index import (
	FAVORITE_ARTICLE_LIMIT,
	get_favorite_articles_by_page_view,
)


class TestSupportIndex(ERPNextTestSuite):
	def make_help_category(self):
		category_name = "_Test Support Category " + random_string(8)
		category = frappe.get_doc(
			{
				"doctype": "Help Category",
				"category_name": category_name,
				"published": 1,
			}
		).insert(ignore_permissions=True)
		return category.name

	def make_help_article(self, category, route, title, content, published=1):
		article = frappe.get_doc(
			{
				"doctype": "Help Article",
				"title": title,
				"category": category,
				"content": content,
				"route": route,
				"published": published,
			}
		).insert(ignore_permissions=True)
		return article.name

	def seed_page_views(self, path, count):
		# Web Page View is in_create/read_only; insert the minimal row the
		# lookup reads (path matched against Help Article.route) directly.
		for _ in range(count):
			view = frappe.new_doc("Web Page View")
			view.path = path
			view.is_unique = "1"
			view.flags.name_set = True
			view.name = frappe.generate_hash("wpv", 12)
			view.db_insert()

	def test_favorite_articles_ordered_by_page_view_count(self):
		category = self.make_help_category()

		# Distinct, collision-free routes so other published articles in the DB
		# can't masquerade as ours.
		route_hi = "support-hi-" + random_string(10)
		route_lo = "support-lo-" + random_string(10)

		name_hi = self.make_help_article(
			category, route_hi, "High Views Article", "<p>High views content</p>"
		)
		name_lo = self.make_help_article(category, route_lo, "Low Views Article", "<p>Low views content</p>")

		# More views on route_hi than route_lo: a broken Count/GROUP BY/ORDER BY
		# would not reproduce these exact counts or this ordering.
		self.seed_page_views(route_hi, 3)
		self.seed_page_views(route_lo, 1)

		results = get_favorite_articles_by_page_view()

		by_route = {row.route: row for row in results if row.route in (route_hi, route_lo)}

		# Both of our routes are surfaced by matching path against route.
		self.assertIn(route_hi, by_route, "High-viewed route missing from results")
		self.assertIn(route_lo, by_route, "Low-viewed route missing from results")

		# The aliased count reflects the real number of seeded Web Page View rows. Reading it
		# under a driver-specific key such as "COUNT(*)" would raise KeyError on postgres.
		self.assertEqual(by_route[route_hi]["count"], 3)
		self.assertEqual(by_route[route_lo]["count"], 1)

		# The display fields come from the article's own row, including the body, which is read
		# only for the articles that survive the ranking.
		self.assertEqual(by_route[route_hi].name, name_hi)
		self.assertEqual(by_route[route_hi].title, "High Views Article")
		self.assertEqual(by_route[route_hi].category, category)
		self.assertEqual(by_route[route_hi].content, "<p>High views content</p>")
		self.assertEqual(by_route[route_lo].name, name_lo)

		# Ranked by count, descending: the higher-viewed route precedes the lower one.
		ordered_routes = [row.route for row in results if row.route in (route_hi, route_lo)]
		self.assertEqual(
			ordered_routes,
			[route_hi, route_lo],
			"Results not ordered by page-view count descending",
		)

	def test_mixed_case_route_is_matched_and_counted(self):
		"""A route stored with capitals must still find the views recorded against it.

		The two halves of the lookup are case-sensitive in opposite directions, and this covers
		both: the `in` filter is sent the route as stored, so a case-sensitive backend matches it
		at all, and the returned path is folded before lookup, because MariaDB groups
		case-insensitively and answers under an arbitrary spelling from the group.
		"""
		category = self.make_help_category()
		route = "Support-Mixed-" + random_string(10)
		self.assertNotEqual(route, route.lower(), "route must contain capitals to be a regression")

		name = self.make_help_article(category, route, "Mixed Case Route", "<p>Mixed</p>")
		self.seed_page_views(route, 4)

		by_name = {row.name: row for row in get_favorite_articles_by_page_view()}

		self.assertIn(name, by_name, "article with a mixed-case route was dropped")
		self.assertEqual(by_name[name]["count"], 4)
		self.assertEqual(by_name[name].route, route)

	def test_case_variant_paths_do_not_break_the_page(self):
		"""Views recorded at a differently-cased spelling of a route must not raise.

		Whether they also count towards the article is the backend collation's call -- MariaDB
		folds them into the route's group, postgres and SQLite do not -- so this asserts the
		invariant that holds on all three: the article is returned, and no spelling of its path
		can cost it the views recorded at the route itself.
		"""
		category = self.make_help_category()
		route = "support-variant-" + random_string(10)
		name = self.make_help_article(category, route, "Variant Article", "<p>Variant</p>")

		self.seed_page_views(route, 2)
		self.seed_page_views(route.upper(), 5)

		by_name = {row.name: row for row in get_favorite_articles_by_page_view()}

		self.assertIn(name, by_name, "case variant dropped the article from the results")
		self.assertGreaterEqual(by_name[name]["count"], 2)

	def test_view_paths_without_an_article_are_ignored(self):
		"""A page view whose path matches no published article contributes nothing."""
		category = self.make_help_category()
		route = "support-real-" + random_string(10)
		name = self.make_help_article(category, route, "Real Article", "<p>Real</p>")

		self.seed_page_views(route, 2)
		self.seed_page_views("support-ghost-" + random_string(10), 50)

		results = get_favorite_articles_by_page_view()
		by_name = {row.name: row for row in results}

		self.assertIn(name, by_name)
		self.assertEqual(by_name[name]["count"], 2)
		# The ghost path's 50 views were not attributed to any article.
		self.assertNotIn(50, [row["count"] for row in results])

	def test_unviewed_article_is_not_returned(self):
		"""A published article with no page views is not a favorite article."""
		category = self.make_help_category()
		route = "support-unviewed-" + random_string(10)
		name = self.make_help_article(category, route, "Unviewed Article", "<p>Unviewed</p>")

		names = [row.name for row in get_favorite_articles_by_page_view()]

		self.assertNotIn(name, names)

	def test_result_is_limited_to_six_articles(self):
		"""At most FAVORITE_ARTICLE_LIMIT articles come back, and they are the most viewed."""
		category = self.make_help_category()

		# Eight candidates with distinct, descending view counts, so the two that fall outside
		# the limit are unambiguous. Articles with no views never appear, so nothing else in the
		# site's data can compete for the six slots.
		expected = []
		for index in range(8):
			route = f"support-limit-{index}-" + random_string(10)
			name = self.make_help_article(category, route, f"Limit Article {index}", "<p>Limit</p>")
			self.seed_page_views(route, 20 - index)
			expected.append(name)

		results = get_favorite_articles_by_page_view()

		self.assertEqual(len(results), FAVORITE_ARTICLE_LIMIT)
		self.assertEqual([row.name for row in results], expected[:FAVORITE_ARTICLE_LIMIT])
		self.assertEqual([row["count"] for row in results], [20, 19, 18, 17, 16, 15])
