# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import datetime

import frappe
from frappe import _
from frappe.model.document import Document


class SocialMediaPost(Document):
	def validate(self):
		if not self.twitter and not self.linkedin:
			frappe.throw(_("Select atleast one Social Media Platform to Share on."))

		if self.scheduled_time:
			current_time = frappe.utils.now_datetime()
			scheduled_time = frappe.utils.get_datetime(self.scheduled_time)
			if scheduled_time < current_time:
				frappe.throw(_("Scheduled Time must be a future time."))

		if self.text and len(self.text) > 280:
			frappe.throw(_("Tweet length must be less than 280."))

	def submit(self):
		if self.scheduled_time:
			self.post_status = "Scheduled"
		super(SocialMediaPost, self).submit()

	def on_cancel(self):
		self.db_set("post_status", "Cancelled")

	@frappe.whitelist()
	def delete_post(self):
		if self.twitter and self.twitter_post_id:
			twitter = frappe.get_doc("Twitter Settings")
			twitter.delete_tweet(self.twitter_post_id)

		if self.linkedin and self.linkedin_post_id:
			linkedin = frappe.get_doc("LinkedIn Settings")
			linkedin.delete_post(self.linkedin_post_id)

		self.db_set("post_status", "Deleted")

	@frappe.whitelist()
	def get_post(self):
		response = {}
		if self.linkedin and self.linkedin_post_id:
			linkedin = frappe.get_doc("LinkedIn Settings")
			response["linkedin"] = linkedin.get_post(self.linkedin_post_id)
		if self.twitter and self.twitter_post_id:
			twitter = frappe.get_doc("Twitter Settings")
			response["twitter"] = twitter.get_tweet(self.twitter_post_id)

		return response

	@frappe.whitelist()
	def post(self):
		try:
			if self.twitter and not self.twitter_post_id:
				twitter = frappe.get_doc("Twitter Settings")
				twitter_post = twitter.post(self.text, self.image)
				self.db_set("twitter_post_id", twitter_post.id)
			if self.linkedin and not self.linkedin_post_id:
				linkedin = frappe.get_doc("LinkedIn Settings")
				linkedin_post = linkedin.post(self.linkedin_post, self.title, self.image)
				self.db_set("linkedin_post_id", linkedin_post.headers["X-RestLi-Id"])
			self.db_set("post_status", "Posted")

		except Exception:
			self.db_set("post_status", "Error")
			title = _("Error while POSTING {0}").format(self.name)
			frappe.log_error(message=frappe.get_traceback(), title=title)


def process_scheduled_social_media_posts():
	posts = frappe.get_list(
		"Social Media Post",
		filters={"post_status": "Scheduled", "docstatus": 1},
		fields=["name", "scheduled_time"],
	)
	start = frappe.utils.now_datetime()
	end = start + datetime.timedelta(minutes=10)
	for post in posts:
		if post.scheduled_time:
			post_time = frappe.utils.get_datetime(post.scheduled_time)
			if post_time > start and post_time <= end:
				sm_post = frappe.get_doc("Social Media Post", post.name)
				sm_post.post()
