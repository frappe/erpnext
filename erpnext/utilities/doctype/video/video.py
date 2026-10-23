# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import re
from datetime import datetime
from urllib.parse import parse_qs, urlparse

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime, now_datetime, time_diff_in_hours
from pyyoutube import Api

YOUTUBE_DOMAINS = ("youtube.com", "youtu.be", "youtube-nocookie.com")
YOUTUBE_VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")


class Video(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		comment_count: DF.Float
		description: DF.TextEditor
		dislike_count: DF.Float
		duration: DF.Duration | None
		image: DF.AttachImage | None
		like_count: DF.Float
		provider: DF.Literal["YouTube", "Vimeo"]
		publish_date: DF.Date | None
		title: DF.Data
		url: DF.Data
		view_count: DF.Float
		youtube_video_id: DF.Data | None
	# end: auto-generated types

	def validate(self):
		if self.provider != "YouTube":
			return

		self.set_video_id()
		if is_tracking_enabled():
			self.set_youtube_statistics()

	def set_video_id(self):
		if self.url and (not self.get("youtube_video_id") or self.has_value_changed("url")):
			self.youtube_video_id = get_id_from_url(self.url)

	def set_youtube_statistics(self):
		api_key = frappe.db.get_single_value("Video Settings", "api_key")

		try:
			api = Api(api_key=api_key)
			video = api.get_video_by_id(video_id=self.youtube_video_id)
			video_stats = video.items[0].to_dict().get("statistics")

			self.like_count = video_stats.get("likeCount")
			self.view_count = video_stats.get("viewCount")
			self.dislike_count = video_stats.get("dislikeCount")
			self.comment_count = video_stats.get("commentCount")

		except Exception:
			self.log_error("Unable to update YouTube statistics")


def is_tracking_enabled():
	return frappe.db.get_single_value("Video Settings", "enable_youtube_tracking")


def update_youtube_data():
	"""Runs hourly via hooks; updates the statistics once the chosen frequency has passed."""
	video_settings = frappe.get_single("Video Settings")
	if not video_settings.enable_youtube_tracking or not is_update_due(video_settings):
		return

	batch_update_youtube_data()
	frappe.db.set_single_value("Video Settings", "last_youtube_update", now_datetime())


def is_update_due(video_settings: Document) -> bool:
	if not video_settings.last_youtube_update:
		return True

	# compare hourly slots so that a job starting a few minutes late still runs
	hours_since_update = time_diff_in_hours(
		start_of_hour(now_datetime()), start_of_hour(get_datetime(video_settings.last_youtube_update))
	)
	return hours_since_update >= get_frequency_in_hours(video_settings.frequency)


def get_frequency_in_hours(frequency: str | None) -> int:
	# the removed "30 mins" option falls back to hourly
	return {"6 hrs": 6, "Daily": 24}.get(frequency, 1)


def start_of_hour(value: datetime) -> datetime:
	return value.replace(minute=0, second=0, microsecond=0)


def get_formatted_ids(video_list):
	# format ids to comma separated string for bulk request
	ids = []
	for video in video_list:
		ids.append(video.youtube_video_id)

	return ",".join(ids)


@frappe.whitelist()
def get_id_from_url(url: str):
	"""
	Returns video id from url
	:param youtube url: String URL
	"""
	if not isinstance(url, str):
		frappe.throw(_("URL can only be a string"), title=_("Invalid URL"))

	video_id = parse_youtube_video_id(url)
	if not video_id:
		frappe.throw(_("Could not find a YouTube video ID in the URL"), title=_("Invalid URL"))

	return video_id


def parse_youtube_video_id(url: str) -> str | None:
	parsed = urlparse(url.strip() if "://" in url else f"https://{url.strip()}")
	host = parsed.hostname or ""
	if not any(host == domain or host.endswith(f".{domain}") for domain in YOUTUBE_DOMAINS):
		return None

	segments = [segment for segment in parsed.path.split("/") if segment]
	if host.endswith("youtu.be"):
		video_id = segments[0] if segments else None
	elif len(segments) > 1 and segments[0] in ("embed", "shorts", "live", "v"):
		video_id = segments[1]
	else:
		video_id = parse_qs(parsed.query).get("v", [None])[0]

	return video_id if video_id and YOUTUBE_VIDEO_ID.fullmatch(video_id) else None


@frappe.whitelist()
def batch_update_youtube_data():
	frappe.has_permission("Video Settings", "write", throw=True)

	def get_youtube_statistics(video_ids):
		api_key = frappe.db.get_single_value("Video Settings", "api_key")
		api = Api(api_key=api_key)
		try:
			video = api.get_video_by_id(video_id=video_ids)
			video_stats = video.items
			return video_stats
		except Exception:
			frappe.log_error("Unable to update YouTube statistics")

	def prepare_and_set_data(video_list):
		video_ids = get_formatted_ids(video_list)
		stats = get_youtube_statistics(video_ids)
		if stats:
			set_youtube_data(stats)

	def set_youtube_data(entries):
		for entry in entries:
			video_stats = entry.to_dict().get("statistics")
			video_id = entry.to_dict().get("id")
			stats = {
				"like_count": cint(video_stats.get("likeCount")),
				"view_count": cint(video_stats.get("viewCount")),
				"dislike_count": cint(video_stats.get("dislikeCount")),
				"comment_count": cint(video_stats.get("commentCount")),
			}
			frappe.db.set_value("Video", {"youtube_video_id": video_id}, stats)

	video_list = frappe.get_all(
		"Video",
		filters={"provider": "YouTube", "youtube_video_id": ["is", "set"]},
		fields=["youtube_video_id"],
	)
	if len(video_list) > 50:
		# Update in batches of 50
		start, end = 0, 50
		while start < len(video_list):
			batch = video_list[start:end]
			prepare_and_set_data(batch)
			start += 50
			end += 50
	else:
		prepare_and_set_data(video_list)
