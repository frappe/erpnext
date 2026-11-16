# Copyright (c) 2021, Wahni Green Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
from fnmatch import fnmatch
from unittest.mock import Mock, patch

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import CallbackManager
from frappe.utils.redis_wrapper import RedisWrapper

from erpnext.accounts.doctype.currency_exchange_settings.currency_exchange_settings import (
	CurrencyExchangeSettings,
)
from erpnext.setup.utils import get_exchange_rate


class TestCurrencyExchangeSettings(UnitTestCase):
	def test_clear_provider_rates_after_commit(self):
		with patch(
			"erpnext.accounts.doctype.currency_exchange_settings.currency_exchange_settings.frappe"
		) as mock_frappe:
			mock_frappe.db.after_commit = CallbackManager()
			rates = {"currency_exchange_rate_USD_INR": 80}
			mock_frappe.cache.delete_keys.side_effect = lambda *args, **kwargs: rates.clear()

			CurrencyExchangeSettings.on_update(None)

			self.assertEqual(rates, {})
			mock_frappe.cache.delete_keys.assert_called_once_with("currency_exchange_rate_")

			# A concurrent lookup still sees the old settings until the save commits.
			rates["currency_exchange_rate_USD_INR"] = 80
			mock_frappe.db.after_commit.run()

			self.assertEqual(rates, {})
			self.assertEqual(mock_frappe.cache.delete_keys.call_count, 2)
			mock_frappe.cache.delete_keys.assert_called_with("currency_exchange_rate_")

	def test_website_user_can_use_local_rates_but_not_request_provider(self):
		with (
			patch("erpnext.setup.utils.frappe") as mock_frappe,
			patch("erpnext.setup.utils.is_system_user", return_value=False),
			patch("requests.get") as request,
		):
			mock_frappe.PermissionError = frappe.PermissionError
			mock_frappe.throw.side_effect = frappe.PermissionError
			mock_frappe.get_cached_doc.return_value = frappe._dict(allow_stale=1)
			mock_frappe.get_single_value.return_value = 0
			mock_frappe.get_all.return_value = [frappe._dict(exchange_rate=80)]
			self.assertEqual(get_exchange_rate("USD", "INR", "2026-01-01"), 80)
			self.assertEqual(get_exchange_rate("USD", "USD", "2026-01-01"), 1)

			mock_frappe.get_all.return_value = []
			mock_frappe.cache.return_value.get_value.return_value = 81
			self.assertEqual(get_exchange_rate("USD", "INR", "2026-01-01"), 81)

			mock_frappe.cache.return_value.get_value.return_value = None
			with self.assertRaises(frappe.PermissionError):
				get_exchange_rate("USD", "INR", "2026-01-01")
			request.assert_not_called()

	def test_provider_cache_is_isolated_between_sites(self):
		cache = RedisWrapper()
		rates = {}
		settings = frappe._dict(
			allow_stale=1,
			api_endpoint="https://example.com/rates",
			req_params=[],
			result_key=[],
		)
		with (
			patch.object(frappe.local, "conf", frappe._dict(db_name="site_one")),
			patch.object(frappe.local, "cache", {}),
			patch.object(frappe, "cache", cache),
			patch.object(frappe, "db", Mock()) as database,
			patch.object(frappe, "get_all", return_value=[]),
			patch.object(frappe, "get_single_value", return_value=0),
			patch.object(frappe, "get_cached_doc", return_value=settings),
			patch("erpnext.setup.utils.is_system_user", return_value=True),
			patch("requests.get") as request,
			patch.object(cache, "get", side_effect=rates.get),
			patch.object(cache, "set") as store,
			patch.object(
				cache, "keys", side_effect=lambda pattern: [key for key in rates if fnmatch(key, pattern)]
			),
			patch.object(cache, "unlink", side_effect=lambda *keys: [rates.pop(key, None) for key in keys]),
		):
			store.side_effect = lambda name, value, ex: rates.update({name: value})
			request.return_value.json.side_effect = [80, 90]
			self.assertEqual(get_exchange_rate("USD", "INR", "2026-01-01"), 80)
			self.assertEqual(store.call_args.kwargs["ex"], 21600)

			frappe.local.conf.db_name = "site_two"
			self.assertEqual(get_exchange_rate("USD", "INR", "2026-01-01"), 90)
			self.assertEqual(request.call_count, 2)

			frappe.local.conf.db_name = "site_one"
			self.assertEqual(get_exchange_rate("USD", "INR", "2026-01-01"), 80)
			database.after_commit = CallbackManager()
			CurrencyExchangeSettings.on_update(None)
			database.after_commit.run()
			self.assertIsNone(cache.get_value("currency_exchange_rate_2026-01-01:USD:INR"))

			frappe.local.conf.db_name = "site_two"
			self.assertEqual(get_exchange_rate("USD", "INR", "2026-01-01"), 90)
			self.assertEqual(request.call_count, 2)
