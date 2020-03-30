# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class SocialMediaPost(Document):
	def submit(self):
		if not self.is_scheduled:
			self.post()
		else:
			self.status = "Scheduled"

		super(SocialMediaPost, self).submit()

	def post(self):
		if self.twitter:
			twitter = frappe.get_doc("Twitter Settings")
			twitter.post(self.text, self.image)

		if self.linkedin:
			linkedin = frappe.get_doc("LinkedIn Settings")
			linkedin.post(self.text, self.image)
		
		self.status = "Posted"

def process_scheduled_social_media_posts():
	import datetime
	posts = frappe.get_list("Social Media Post", filters={"status": "Scheduled"}, fields= ["name", "scheduled_time"])
	start = frappe.utils.now_datetime()
	end = start + datetime.timedelta(minutes=59)
	for post in posts:
		post_time = frappe.utils.get_datetime(post.scheduled_time)
		if post_time > start and post_time <= end:
			post.post()