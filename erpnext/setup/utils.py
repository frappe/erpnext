# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from math import isfinite
from urllib.parse import quote

import frappe
from frappe import _
from frappe.permissions import is_system_user
from frappe.utils import add_days, flt, get_datetime_str, getdate, nowdate
from frappe.utils.data import DateTimeLikeObject
from frappe.utils.nestedset import get_root_of

from erpnext import get_default_company


def get_pegged_currencies():
	pegged_currencies = frappe.get_all(
		"Pegged Currency Details",
		filters={"parent": "Pegged Currencies"},
		fields=["source_currency", "pegged_against", "pegged_exchange_rate"],
	)

	pegged_map = {
		currency.source_currency: {
			"pegged_against": currency.pegged_against,
			"ratio": flt(currency.pegged_exchange_rate),
		}
		for currency in pegged_currencies
		# a row without a positive ratio cannot convert anything
		if currency.source_currency and currency.pegged_against and flt(currency.pegged_exchange_rate) > 0
	}
	return pegged_map


def get_pegged_rate(pegged_map, from_currency, to_currency, transaction_date=None, args=None):
	"""Return the rate for a pair in which at least one currency is pegged, or None if neither is.

	The ratio of a pegged currency is the number of its units for one unit of the currency it
	is pegged against, e.g. AED pegged against USD at 3.6725.
	"""
	from_entry = pegged_map.get(from_currency)
	to_entry = pegged_map.get(to_currency)

	if not (from_entry or to_entry):
		return None

	# Case 1: both are pegged against the same currency
	if from_entry and to_entry and from_entry["pegged_against"] == to_entry["pegged_against"]:
		return to_entry["ratio"] / from_entry["ratio"]

	# Case 2: from_currency is pegged against to_currency
	if from_entry and from_entry["pegged_against"] == to_currency:
		return 1 / from_entry["ratio"]

	# Case 3: to_currency is pegged against from_currency
	if to_entry and to_entry["pegged_against"] == from_currency:
		return to_entry["ratio"]

	# Otherwise convert between the currencies they are pegged against, from a Currency Exchange
	# record or the provider, the same way as any other pair
	base_from = from_entry["pegged_against"] if from_entry else from_currency
	base_to = to_entry["pegged_against"] if to_entry else to_currency
	base_rate = _get_exchange_rate(base_from, base_to, transaction_date, args, resolve_pegged=False)
	if not base_rate:
		return 0.0

	rate = flt(base_rate)
	if from_entry:
		rate /= from_entry["ratio"]
	if to_entry:
		rate *= to_entry["ratio"]
	return rate


@frappe.whitelist()
def get_exchange_rate(
	from_currency: str | None = None,
	to_currency: str | None = None,
	transaction_date: DateTimeLikeObject | None = None,
	args: str | None = None,
):
	return _get_exchange_rate(from_currency, to_currency, transaction_date, args)


def _get_exchange_rate(from_currency, to_currency, transaction_date=None, args=None, resolve_pegged=True):
	if not (from_currency and to_currency):
		# manqala 19/09/2016: Should this be an empty return or should it throw and exception?
		return
	for currency in (from_currency, to_currency):
		if not isinstance(currency, str) or not frappe.db.exists("Currency", currency):
			frappe.throw(_("Invalid currency: {0}").format(currency))

	if from_currency == to_currency:
		return 1

	transaction_date = getdate(transaction_date)
	if not transaction_date:
		frappe.throw(_("Invalid transaction date"))
	transaction_date = transaction_date.isoformat()

	currency_settings = frappe.get_cached_doc("Accounts Settings")
	allow_stale_rates = currency_settings.get("allow_stale")

	filters = [
		["date", "<=", get_datetime_str(transaction_date)],
		["from_currency", "=", from_currency],
		["to_currency", "=", to_currency],
	]

	if args == "for_buying":
		filters.append(["for_buying", "=", "1"])
	elif args == "for_selling":
		filters.append(["for_selling", "=", "1"])

	if not allow_stale_rates:
		stale_days = currency_settings.get("stale_days")
		checkpoint_date = add_days(transaction_date, -stale_days)
		filters.append(["date", ">", get_datetime_str(checkpoint_date)])

	# cksgb 19/09/2016: get last entry in Currency Exchange with from_currency and to_currency.
	entries = frappe.get_all(
		"Currency Exchange",
		fields=["exchange_rate"],
		filters=filters,
		order_by="date desc, name desc",
		limit=1,
	)
	if entries:
		return flt(entries[0].exchange_rate)

	# fixed pegs need no provider, so they are resolved before the provider check
	if resolve_pegged and currency_settings.allow_pegged_currencies_exchange_rates:
		rate = get_pegged_rate(get_pegged_currencies(), from_currency, to_currency, transaction_date, args)
		if rate is not None:
			return flt(rate)

	if frappe.get_single_value("Currency Exchange Settings", "disabled"):
		return 0.00

	try:
		cache = frappe.cache()
		key = f"currency_exchange_rate_{transaction_date}:{from_currency}:{to_currency}"
		value = cache.get_value(key)

		if not value:
			if not is_system_user():
				frappe.throw(
					_("Only system users can fetch exchange rates from an external provider."),
					frappe.PermissionError,
				)

			import requests

			from erpnext.accounts.doctype.currency_exchange_settings.currency_exchange_settings import (
				get_auth_params,
			)

			settings = frappe.get_cached_doc("Currency Exchange Settings")
			req_params = {
				"transaction_date": transaction_date,
				"from_currency": from_currency,
				"to_currency": to_currency,
			}
			params = {}
			for row in settings.req_params:
				params[row.key] = format_ces_api(row.value, req_params)
			params.update(get_auth_params(settings))
			response = requests.get(
				format_ces_api(
					settings.api_endpoint, {key: quote(value, safe="") for key, value in req_params.items()}
				),
				params=params,
				timeout=frappe.conf.get("currency_exchange_request_timeout") or 10,
			)
			# expire in 6 hours
			response.raise_for_status()
			value = response.json()
			for res_key in settings.result_key:
				value = value[format_ces_api(str(res_key.key), req_params)]
			if isinstance(value, bool):
				raise ValueError("Invalid exchange rate")
			value = float(value)
			if not isfinite(value) or value <= 0:
				raise ValueError("Exchange rate must be a positive finite number")
			cache.set_value(key, value, expires_in_sec=21600)

		value = float(value)
		if not isfinite(value) or value <= 0:
			raise ValueError("Exchange rate must be a positive finite number")

		return flt(value)
	except frappe.PermissionError:
		raise
	except Exception:
		frappe.log_error("Unable to fetch exchange rate")
		frappe.msgprint(
			_(
				"Unable to find exchange rate for {0} to {1} for key date {2}. Please create a Currency Exchange record manually"
			).format(from_currency, to_currency, transaction_date)
		)
		return 0.0


def format_ces_api(data, param):
	return data.format(
		transaction_date=param.get("transaction_date"),
		to_currency=param.get("to_currency"),
		from_currency=param.get("from_currency"),
	)


def enable_all_roles_and_domains():
	"""enable all roles and domain for testing"""
	_enable_all_roles_for_admin()


def _enable_all_roles_for_admin():
	from frappe.desk.page.setup_wizard.setup_wizard import add_all_roles_to

	all_roles = set(frappe.get_all("Role", pluck="name"))
	admin_roles = set(
		frappe.db.get_values("Has Role", {"parent": "Administrator"}, fieldname="role", pluck="role")
	)

	if all_roles.difference(admin_roles):
		add_all_roles_to("Administrator")


def set_defaults_for_tests():
	defaults = {
		"customer_group": get_root_of("Customer Group"),
		"territory": get_root_of("Territory"),
	}
	frappe.db.set_single_value("Selling Settings", defaults)
	for key, value in defaults.items():
		frappe.db.set_default(key, value)
	frappe.db.set_single_value("Stock Settings", "auto_insert_price_list_rate_if_missing", 0)

	frappe.db.set_single_value("Stock Settings", "enable_serial_and_batch_no_for_item", 1)


def insert_record(records):
	from frappe.desk.page.setup_wizard.setup_wizard import make_records

	make_records(records)


def welcome_email():
	site_name = get_default_company() or "ERPNext"
	title = _("Welcome to {0}").format(site_name)
	return title
