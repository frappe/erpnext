# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from pyyoutube import Api, PyYouTubeException


class VideoSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		api_key: DF.Data | None
		enable_youtube_tracking: DF.Check
		frequency: DF.Literal["30 mins", "1 hr", "6 hrs", "Daily"]
	# end: auto-generated types

	def validate(self):
		self.validate_tracking_settings()
		self.validate_youtube_api_key()

	def validate_tracking_settings(self):
		if not self.enable_youtube_tracking:
			return

		for fieldname in ("api_key", "frequency"):
			if not self.get(fieldname):
				frappe.throw(
					_("{0} is required to enable YouTube tracking").format(_(self.meta.get_label(fieldname)))
				)

	def validate_youtube_api_key(self):
		if self.enable_youtube_tracking and self.api_key:
			try:
				Api(api_key=self.api_key).get_i18n_languages(parts="snippet")
			except Exception:
				self.log_error("Failed to authenticate API key")
				frappe.throw(
					_("Failed to authenticate the API key. Please check the error logs."),
					title=_("Invalid Credentials"),
				)
