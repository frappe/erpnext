# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe.model.document import Document
from six import string_types
from pyyoutube import Api

class Video(Document):
	pass

@frappe.whitelist()
def get_video_stats(docname, youtube_id, update=True):
	'''Returns/Sets video statistics

	:param docname: Name of Video
	:param youtube_id: Unique ID from URL
	:param update: Updates db stats value if True, else returns statistics
	'''
	if isinstance(update, string_types):
		update = json.loads(update)

	api_key = frappe.db.get_single_value("Video Settings", "api_key")
	api = Api(api_key=api_key)

	try:
		video = api.get_video_by_id(video_id=youtube_id)
		video_stats = video.items[0].to_dict().get('statistics')
		stats = {
			'like_count' : video_stats.get('likeCount'),
			'view_count' : video_stats.get('viewCount'),
			'dislike_count' : video_stats.get('dislikeCount'),
			'comment_count' : video_stats.get('commentCount')
		}

		if not update:
			return stats

		frappe.db.sql("""
			UPDATE `tabVideo`
			SET
				like_count  = %(like_count)s,
				view_count = %(view_count)s,
				dislike_count = %(dislike_count)s,
				comment_count = %(comment_count)s
			WHERE name = {0}""".format(frappe.db.escape(docname)), stats) #nosec
		frappe.db.commit()
	except:
		message = "Please make sure you are connected to the Internet"
		frappe.log_error(message + "\n\n" + frappe.get_traceback(), "Failed to Update YouTube Statistics for Video: {0}".format(docname))