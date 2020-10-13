# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from apiclient.discovery import build

class VideoSettings(Document):
	def validate(self):
		self.validate_youtube_api_key()

	def validate_youtube_api_key(self):
		if self.enable_youtube_tracking and self.api_key:
			try:
				build("youtube", "v3", developerKey=self.api_key)
			except Exception:
				title = _("Failed to Authenticate the API key.")
				frappe.log_error(title + "\n\n" +  frappe.get_traceback(), title=title)
				frappe.throw(title + " Please check the error logs.", title=_("Invalid Credentials"))