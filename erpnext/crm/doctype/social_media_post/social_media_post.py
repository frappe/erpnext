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