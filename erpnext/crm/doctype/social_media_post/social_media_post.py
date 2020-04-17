# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class SocialMediaPost(Document):
	def submit(self):
		if self.sheduled_time:
			self.post_status = "Scheduled"
		super(SocialMediaPost, self).submit()

	def post(self):
		try:
			if self.twitter and not self.twitter_post_id:
				twitter = frappe.get_doc("Twitter Settings")
				twitter_post = twitter.post(self.text, self.image)
				self.db_set("twitter_post_id", twitter_post.id)
			if self.linkedin and not self.linkedin_post_id:
				linkedin = frappe.get_doc("LinkedIn Settings")
				linkedin_post = linkedin.post(self.linkedin_post, self.image)
				self.db_set("linkedin_post_id", linkedin_post.headers['X-RestLi-Id'].split(":")[-1])
			self.db_set("post_status", "Posted")

		except Exception as e:
			self.db_set("post_status", "Error")
			title = _("Error while POSTING {0}").format(self.name)
			traceback = frappe.get_traceback()
			frappe.log_error(message=traceback , title=title)

def process_scheduled_social_media_posts():
	import datetime
	posts = frappe.get_list("Social Media Post", filters={"status": "Scheduled"}, fields= ["name", "sheduled_time"])
	start = frappe.utils.now_datetime()
	end = start + datetime.timedelta(minutes=59)
	for post in posts:
		post_time = frappe.utils.get_datetime(post.scheduled_time)
		if post_time > start and post_time <= end:
			post = frappe.get_doc('Social Media Post',post['name'])
			post.post()

@frappe.whitelist()
def publish(doctype, name):
	sm_post = frappe.get_doc(doctype, name)
	sm_post.post()
	frappe.db.commit()
