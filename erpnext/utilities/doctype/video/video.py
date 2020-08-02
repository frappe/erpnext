# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from pyyoutube import Api

class Video(Document):
	pass

@frappe.whitelist()
def update_video_stats(youtube_id):
	'''
	:param youtube_id: Unique ID from URL
	'''
	api_key = frappe.db.get_single_value("Video Settings", "api_key")
	api = Api(api_key=api_key)

	video = api.get_video_by_id(video_id=youtube_id)
	video_stats = video.items[0].to_dict().get('statistics')
	return {
		'like_count' : video_stats.get('likeCount'),
		'view_count' : video_stats.get('viewCount'),
		'dislike_count' : video_stats.get('dislikeCount'),
		'comment_count' : video_stats.get('commentCount')
	}