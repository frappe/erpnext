# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class SupportSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.support.doctype.support_search_source.support_search_source import (
			SupportSearchSource,
		)

		allow_resetting_service_level_agreement: DF.Check
		close_issue_after_days: DF.Int
		forum_url: DF.Data | None
		get_latest_query: DF.Data | None
		get_started_sections: DF.Code | None
		greeting_subtitle: DF.Data | None
		greeting_title: DF.Data | None
		post_description_key: DF.Data | None
		post_route_key: DF.Data | None
		post_route_string: DF.Data | None
		post_title_key: DF.Data | None
		response_key_list: DF.Data | None
		search_apis: DF.Table[SupportSearchSource]
		show_latest_forum_posts: DF.Check
		track_service_level_agreement: DF.Check
	# end: auto-generated types

	pass
