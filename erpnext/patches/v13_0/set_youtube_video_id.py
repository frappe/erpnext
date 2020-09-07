from __future__ import unicode_literals
import frappe
from erpnext.utilities.doctype.video.video import get_id_from_url

def execute():
	frappe.reload_doc("utilities", "doctype","video")

	for video in frappe.get_all("Video", fields=["name", "url", "youtube_video_id"]):
		if video.url and not video.youtube_video_id:
			frappe.db.set_value("Video", video.name, "youtube_video_id", get_id_from_url(video.url))