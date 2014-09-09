# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe import _
from frappe.utils import nowdate
from frappe.templates.pages.style_settings import default_properties

class website_maker(object):
	def __init__(self, company, tagline, user):
		self.company = company
		self.tagline = tagline
		self.user = user
		self.make_web_page()
		self.make_style_settings()
		self.make_website_settings()
		self.make_blog()

	def make_web_page(self):
		# home page
		self.webpage = frappe.get_doc({
			"doctype": "Web Page",
			"title": self.company,
			"published": 1,
			"header": "<h1>{0}</h1>".format(self.tagline or "Headline")+\
				'<p>'+_("This is an example website auto-generated from ERPNext")+"</p>"+\
				'<p><a class="btn btn-primary" href="/login">Login</a></p>',
			"description": self.company + ":" + (self.tagline or ""),
			"css": frappe.get_template("setup/page/setup_wizard/sample_home_page.css").render(),
			"main_section": frappe.get_template("setup/page/setup_wizard/sample_home_page.html").render({
				"company": self.company, "tagline": (self.tagline or "")
			})
		}).insert()

	def make_style_settings(self):
		style_settings = frappe.get_doc("Style Settings", "Style Settings")
		style_settings.update(default_properties)
		style_settings.apply_style = 1
		style_settings.save()

	def make_website_settings(self):
		# update in home page in settings
		website_settings = frappe.get_doc("Website Settings", "Website Settings")
		website_settings.home_page = self.webpage.name
		website_settings.brand_html = self.company
		website_settings.copyright = self.company
		website_settings.top_bar_items = []
		website_settings.append("top_bar_items", {
			"doctype": "Top Bar Item",
			"label":"Contact",
			"url": "contact"
		})
		website_settings.append("top_bar_items", {
			"doctype": "Top Bar Item",
			"label":"Blog",
			"url": "blog"
		})
		website_settings.append("top_bar_items", {
			"doctype": "Top Bar Item",
			"label": _("Products"),
			"url": "products"
		})
		website_settings.save()

	def make_blog(self):
		blogger = frappe.new_doc("Blogger")
		user = frappe.get_doc("User", self.user)
		blogger.user = self.user
		blogger.full_name = user.first_name + (" " + user.last_name if user.last_name else "")
		blogger.short_name = user.first_name.lower()
		blogger.avatar = user.user_image
		blogger.insert()

		blog_category = frappe.get_doc({
			"doctype": "Blog Category",
			"category_name": "general",
			"published": 1,
			"title": _("General")
		}).insert()

		frappe.get_doc({
			"doctype": "Blog Post",
			"title": "Welcome",
			"published": 1,
			"published_on": nowdate(),
			"blogger": blogger.name,
			"blog_category": blog_category.name,
			"blog_intro": "My First Blog",
			"content": frappe.get_template("setup/page/setup_wizard/sample_blog_post.html").render(),
		}).insert()

def test():
	frappe.delete_doc("Web Page", "test-company")
	frappe.delete_doc("Blog Post", "welcome")
	frappe.delete_doc("Blogger", "administrator")
	frappe.delete_doc("Blog Category", "general")
	website_maker("Test Company", "Better Tools for Everyone", "Administrator")
	frappe.db.commit()
