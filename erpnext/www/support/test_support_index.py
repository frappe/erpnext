# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import random_string
from frappe.utils.logging import get_log_db

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.www.support.index import (
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
		# The log database is not rolled back between tests, so delete the rows afterwards.
		self.addCleanup(get_log_db().delete, "Web Page View", {"path": path})
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

		# The aliased count reflects the real number of seeded Web Page View rows.
		self.assertEqual(by_route[route_hi]["count"], 3)
		self.assertEqual(by_route[route_lo]["count"], 1)

		# The display fields come from the article's own row.
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

	def test_routes_differing_only_in_case_are_separate_articles(self):
		"""Each article keeps its own views when two routes differ only in case."""
		category = self.make_help_category()
		route = "support-case-" + random_string(10)
		name_lower = self.make_help_article(category, route, "Lower Article", "<p>Lower</p>")
		name_upper = self.make_help_article(category, route.upper(), "Upper Article", "<p>Upper</p>")

		self.seed_page_views(route, 2)
		self.seed_page_views(route.upper(), 5)

		by_name = {row.name: row for row in get_favorite_articles_by_page_view()}

		self.assertEqual(by_name[name_lower]["count"], 2)
		self.assertEqual(by_name[name_upper]["count"], 5)
