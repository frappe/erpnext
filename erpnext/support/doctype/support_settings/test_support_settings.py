# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe

from erpnext.templates.pages import help as help_page
from erpnext.tests.utils import ERPNextTestSuite, change_settings

FORUM_SETTINGS = {
	"forum_url": "https://forum.example.com",
	"get_latest_query": "latest.json",
	"response_key_list": "topic_list,topics",
	"post_route_string": "t",
	"post_route_key": "id",
}


class TestSupportSettings(ERPNextTestSuite):
	def test_help_page_respects_default_and_forum_settings(self):
		forum_response = MagicMock()
		forum_response.json.return_value = {"topic_list": {"topics": [{"id": 1}]}}

		with patch.object(help_page.requests, "get", return_value=forum_response) as get:
			with change_settings(
				"Support Settings", get_started_sections=None, show_latest_forum_posts=0, **FORUM_SETTINGS
			):
				context = frappe._dict()
				help_page.get_context(context)
				self.assertEqual(context.get_started_sections, [])
				get.assert_not_called()

			with change_settings("Support Settings", show_latest_forum_posts=1, **FORUM_SETTINGS):
				context = frappe._dict()
				help_page.get_context(context)
				self.assertEqual(context.topics, [{"id": 1, "link": "https://forum.example.com/t/1"}])
				self.assertIn("timeout", get.call_args.kwargs)
