# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.utils import random_string

from erpnext.tests.utils import ERPNextTestSuite
from erpnext.www.support.index import get_favorite_articles_by_page_view


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
		# converted JOIN reads (path == Help Article.route) directly.
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

		# Both of our routes are surfaced by the INNER JOIN on route == path.
		self.assertIn(route_hi, by_route, "High-viewed route missing from results")
		self.assertIn(route_lo, by_route, "Low-viewed route missing from results")

		# Count(route) reflects the real number of seeded Web Page View rows.
		self.assertEqual(by_route[route_hi]["count"], 3)
		self.assertEqual(by_route[route_lo]["count"], 1)

		# Max()-wrapped columns carry the article's own data (one row per route).
		self.assertEqual(by_route[route_hi].name, name_hi)
		self.assertEqual(by_route[route_hi].title, "High Views Article")
		self.assertEqual(by_route[route_hi].category, category)
		self.assertEqual(by_route[route_lo].name, name_lo)

		# ORDER BY count desc: the higher-viewed route precedes the lower one.
		ordered_routes = [row.route for row in results if row.route in (route_hi, route_lo)]
		self.assertEqual(
			ordered_routes,
			[route_hi, route_lo],
			"Results not ordered by page-view count descending",
		)
