# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import ipaddress
import socket
import urllib.parse

import frappe
import requests
from frappe import _
from frappe.utils import add_days, flt, get_datetime_str, nowdate
from frappe.utils.data import DateTimeLikeObject
from frappe.utils.nestedset import get_root_of

from erpnext import get_default_company


def _is_disallowed_ip(ip_str: str) -> bool:
	addr = ipaddress.ip_address(ip_str)
	return (
		addr.is_private
		or addr.is_loopback
		or addr.is_link_local
		or addr.is_reserved
		or addr.is_multicast
		or addr.is_unspecified
	)


def validate_exchange_endpoint(url: str) -> None:
	"""Reject URLs that would allow server-side requests to private/internal addresses."""
	parsed = urllib.parse.urlparse(url)

	if parsed.scheme not in ("http", "https"):
		frappe.throw(_("Exchange rate endpoint must use http or https."), exc=frappe.ValidationError)

	host = parsed.hostname
	if not host:
		frappe.throw(_("Exchange rate endpoint has no valid hostname."), exc=frappe.ValidationError)

	try:
		if _is_disallowed_ip(host):
			frappe.throw(
				_("Exchange rate endpoint must not point to a private or reserved address."),
				exc=frappe.ValidationError,
			)
	except ValueError:
		pass  # hostname, not a bare IP so continue to DNS resolution

	port = parsed.port or (443 if parsed.scheme == "https" else 80)

	try:
		results = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
	except socket.gaierror as e:
		frappe.throw(
			_("Could not resolve exchange rate endpoint hostname: {0}").format(str(e)),
			exc=frappe.ValidationError,
		)

	for _family, _type, _proto, _canonname, sockaddr in results:
		if _is_disallowed_ip(sockaddr[0]):
			frappe.throw(
				_("Exchange rate endpoint resolves to a private or reserved address and cannot be used."),
				exc=frappe.ValidationError,
			)


def safe_ces_request(url: str, params: dict, validate: bool = False):
	if validate:
		validate_exchange_endpoint(url)
	return requests.get(url, params=params, timeout=30)


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
	}
	return pegged_map


def get_pegged_rate(pegged_map, from_currency, to_currency, transaction_date=None):
	from_entry = pegged_map.get(from_currency)
	to_entry = pegged_map.get(to_currency)

	if from_currency in pegged_map and to_currency in pegged_map:
		# Case 1: Both are present and pegged to same bases
		if from_entry["pegged_against"] == to_entry["pegged_against"]:
			return (1 / from_entry["ratio"]) * to_entry["ratio"]

		# Case 2: Both are present but pegged to different bases
		base_from = from_entry["pegged_against"]
		base_to = to_entry["pegged_against"]
		base_rate = get_exchange_rate(base_from, base_to, transaction_date)

		if not base_rate:
			return None

		return (1 / from_entry["ratio"]) * base_rate * to_entry["ratio"]

	# Case 3: from_currency is pegged to to_currency
	if from_entry and from_entry["pegged_against"] == to_currency:
		return flt(from_entry["ratio"])

	# Case 4: to_currency is pegged to from_currency
	if to_entry and to_entry["pegged_against"] == from_currency:
		return 1 / flt(to_entry["ratio"])

	""" If only one entry exists but doesn’t match pegged currency logic, return None """
	return None


@frappe.whitelist()
def get_exchange_rate(
	from_currency: str,
	to_currency: str,
	transaction_date: DateTimeLikeObject | None = None,
	args: str | None = None,
):
	if not (from_currency and to_currency):
		# manqala 19/09/2016: Should this be an empty return or should it throw and exception?
		return
	if from_currency == to_currency:
		return 1

	if not transaction_date:
		transaction_date = nowdate()

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
		"Currency Exchange", fields=["exchange_rate"], filters=filters, order_by="date desc", limit=1
	)
	if entries:
		return flt(entries[0].exchange_rate)

	if frappe.get_cached_value("Currency Exchange Settings", "Currency Exchange Settings", "disabled"):
		return 0.00

	pegged_currencies = {}

	if currency_settings.allow_pegged_currencies_exchange_rates:
		pegged_currencies = get_pegged_currencies()
		if rate := get_pegged_rate(pegged_currencies, from_currency, to_currency, transaction_date):
			return rate

	try:
		cache = frappe.cache()
		key = f"currency_exchange_rate_{transaction_date}:{from_currency}:{to_currency}"
		value = cache.get(key)

		if not value:
			settings = frappe.get_cached_doc("Currency Exchange Settings")
			req_params = {
				"transaction_date": transaction_date,
				"from_currency": from_currency
				if from_currency not in pegged_currencies
				else pegged_currencies[from_currency]["pegged_against"],
				"to_currency": to_currency
				if to_currency not in pegged_currencies
				else pegged_currencies[to_currency]["pegged_against"],
			}
			params = {}
			for row in settings.req_params:
				params[row.key] = format_ces_api(row.value, req_params)
			response = safe_ces_request(
				format_ces_api(settings.api_endpoint, req_params),
				params,
				validate=settings.service_provider == "Custom",
			)
			# expire in 6 hours
			response.raise_for_status()
			value = response.json()
			for res_key in settings.result_key:
				value = value[format_ces_api(str(res_key.key), req_params)]
			cache.setex(name=key, time=21600, value=flt(value))

		# Support multiple pegged currencies
		value = flt(value)

		if currency_settings.allow_pegged_currencies_exchange_rates and to_currency in pegged_currencies:
			value *= flt(pegged_currencies[to_currency]["ratio"])
		if currency_settings.allow_pegged_currencies_exchange_rates and from_currency in pegged_currencies:
			value /= flt(pegged_currencies[from_currency]["ratio"])

		return flt(value)
	except frappe.ValidationError:
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


def identity(x, *args, **kwargs):
	"""Used for redefining the translation function to return the string as is.

	We want to create english records but still mark the strings as translatable.
	E.g. when the respective DocTypes have 'Translate Link Fields' enabled or
	we're creating custom fields.

	Use like this: `from erpnext.setup.utils import identity as _`
	"""
	return x
