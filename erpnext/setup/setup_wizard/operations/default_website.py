# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import nowdate


class website_maker(object):
	def __init__(self, args):
		self.args = args
		self.company = args.company_name
		self.tagline = args.company_tagline
		self.user = args.get('email')
		self.make_web_page()
		self.make_website_settings()
		self.make_blog()

	def make_web_page(self):
		# home page
		homepage = frappe.get_doc('Homepage', 'Homepage')
		homepage.company = self.company
		homepage.tag_line = self.tagline
		homepage.setup_items()
		homepage.save()

	def make_website_settings(self):
		# update in home page in settings
		website_settings = frappe.get_doc("Website Settings", "Website Settings")
		website_settings.home_page = 'home'
		website_settings.brand_html = self.company
		website_settings.copyright = self.company
		website_settings.top_bar_items = []
		website_settings.append("top_bar_items", {
			"doctype": "Top Bar Item",
			"label":"Contact",
			"url": "/contact"
		})
		website_settings.append("top_bar_items", {
			"doctype": "Top Bar Item",
			"label":"Blog",
			"url": "/blog"
		})
		website_settings.append("top_bar_items", {
			"doctype": "Top Bar Item",
			"label": _("Products"),
			"url": "/all-products"
		})
		website_settings.save()

	def make_blog(self):
		blog_category = frappe.get_doc({
			"doctype": "Blog Category",
			"category_name": "general",
			"published": 1,
			"title": _("General")
		}).insert()

		if not self.user:
			# Admin setup
			return

		blogger = frappe.new_doc("Blogger")
		user = frappe.get_doc("User", self.user)
		blogger.user = self.user
		blogger.full_name = user.first_name + (" " + user.last_name if user.last_name else "")
		blogger.short_name = user.first_name.lower()
		blogger.avatar = user.user_image
		blogger.insert()

		frappe.get_doc({
			"doctype": "Blog Post",
			"title": "Welcome",
			"published": 1,
			"published_on": nowdate(),
			"blogger": blogger.name,
			"blog_category": blog_category.name,
			"blog_intro": "My First Blog",
			"content": frappe.get_template("setup/setup_wizard/data/sample_blog_post.html").render(),
		}).insert()

def test():
	frappe.delete_doc("Web Page", "test-company")
	frappe.delete_doc("Blog Post", "welcome")
	frappe.delete_doc("Blogger", "administrator")
	frappe.delete_doc("Blog Category", "general")
	website_maker({'company':"Test Company", 'company_tagline': "Better Tools for Everyone", 'name': "Administrator"})
	frappe.db.commit()
