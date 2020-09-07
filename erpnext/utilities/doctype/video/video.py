# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
import re
from frappe.model.document import Document
from frappe import _
from six import string_types
from pyyoutube import Api

class Video(Document):
	def validate(self):
		self.set_youtube_statistics()

	def set_youtube_statistics(self):
		tracking_enabled = frappe.db.get_single_value("Video Settings", "enable_youtube_tracking")
		if self.provider == "YouTube" and not tracking_enabled:
			return

		api_key = frappe.db.get_single_value("Video Settings", "api_key")
		youtube_id = get_id_from_url(self.url)
		api = Api(api_key=api_key)

		try:
			video = api.get_video_by_id(video_id=youtube_id)
			video_stats = video.items[0].to_dict().get('statistics')

			self.like_count = video_stats.get('likeCount')
			self.view_count = video_stats.get('viewCount')
			self.dislike_count = video_stats.get('dislikeCount')
			self.comment_count = video_stats.get('commentCount')

		except Exception:
			title = "Failed to Update YouTube Statistics for Video: {0}".format(self.name)
			frappe.log_error(title + "\n\n" +  frappe.get_traceback(), title=title)

@frappe.whitelist()
def get_id_from_url(url):
	'''
		Returns video id from url

		:param youtube url: String URL
	'''
	if not isinstance(url, string_types):
		frappe.throw(_("URL can only be a string"), title=_("Invalid URL"))

	pattern = re.compile(r'[a-z\:\//\.]+(youtube|youtu)\.(com|be)/(watch\?v=|embed/|.+\?v=)?([^"&?\s]{11})?')
	id = pattern.match(url)
	return id.groups()[-1]