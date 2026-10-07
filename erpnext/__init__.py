import functools
import inspect

import frappe
from frappe.utils import cstr
from frappe.utils.user import is_website_user

__version__ = "15.122.0"


def get_default_company(user=None):
	"""Get default company for user"""
	from frappe.defaults import get_user_default_as_list

	if not user:
		user = frappe.session.user

	companies = get_user_default_as_list("company", user)
	if companies:
		default_company = companies[0]
	else:
		default_company = frappe.db.get_single_value("Global Defaults", "default_company")

	return default_company


def get_default_currency():
	"""Returns the currency of the default company"""
	company = get_default_company()
	if company:
		return frappe.get_cached_value("Company", company, "default_currency")


def get_default_cost_center(company):
	"""Returns the default cost center of the company"""
	if not company:
		return None

	if not frappe.flags.company_cost_center:
		frappe.flags.company_cost_center = {}
	if company not in frappe.flags.company_cost_center:
		frappe.flags.company_cost_center[company] = frappe.get_cached_value("Company", company, "cost_center")
	return frappe.flags.company_cost_center[company]


def get_company_currency(company):
	"""Returns the default company currency"""
	if not frappe.flags.company_currency:
		frappe.flags.company_currency = {}
	if company not in frappe.flags.company_currency:
		frappe.flags.company_currency[company] = frappe.db.get_value(
			"Company", company, "default_currency", cache=True
		)
	return frappe.flags.company_currency[company]


def set_perpetual_inventory(enable=1, company=None):
	if not company:
		company = "_Test Company" if frappe.flags.in_test else get_default_company()

	company = frappe.get_doc("Company", company)
	company.enable_perpetual_inventory = enable
	company.save()


def encode_company_abbr(name, company=None, abbr=None):
	"""Returns name encoded with company abbreviation"""
	company_abbr = abbr or frappe.get_cached_value("Company", company, "abbr")
	parts = name.rsplit(" - ", 1)

	if parts[-1].lower() != company_abbr.lower():
		parts.append(company_abbr)

	return " - ".join(parts)


def is_perpetual_inventory_enabled(company):
	if not company:
		company = "_Test Company" if frappe.flags.in_test else get_default_company()

	if not hasattr(frappe.local, "enable_perpetual_inventory"):
		frappe.local.enable_perpetual_inventory = {}

	if company not in frappe.local.enable_perpetual_inventory:
		frappe.local.enable_perpetual_inventory[company] = (
			frappe.get_cached_value("Company", company, "enable_perpetual_inventory") or 0
		)

	return frappe.local.enable_perpetual_inventory[company]


def get_default_finance_book(company=None):
	if not company:
		company = get_default_company()

	if not hasattr(frappe.local, "default_finance_book"):
		frappe.local.default_finance_book = {}

	if company not in frappe.local.default_finance_book:
		frappe.local.default_finance_book[company] = frappe.get_cached_value(
			"Company", company, "default_finance_book"
		)

	return frappe.local.default_finance_book[company]


def get_party_account_type(party_type):
	if not hasattr(frappe.local, "party_account_types"):
		frappe.local.party_account_types = {}

	if party_type not in frappe.local.party_account_types:
		frappe.local.party_account_types[party_type] = (
			frappe.db.get_value("Party Type", party_type, "account_type") or ""
		)

	return frappe.local.party_account_types[party_type]


def get_region(company=None):
	"""Return the default country based on flag, company or global settings

	You can also set global company flag in `frappe.flags.company`
	"""

	if not company:
		company = frappe.local.flags.company

	if company:
		return frappe.get_cached_value("Company", company, "country")

	return frappe.flags.country or frappe.get_system_settings("country")


def allow_regional(fn):
	"""Decorator to make a function regionally overridable

	Example:
	@erpnext.allow_regional
	def myfunction():
	  pass"""

	@functools.wraps(fn)
	def caller(*args, **kwargs):
		overrides = frappe.get_hooks("regional_overrides", {}).get(get_region())
		function_path = f"{inspect.getmodule(fn).__name__}.{fn.__name__}"

		if not overrides or function_path not in overrides:
			return fn(*args, **kwargs)

		# Priority given to last installed app
		return frappe.get_attr(overrides[function_path][-1])(*args, **kwargs)

	return caller


def check_app_permission():
	if frappe.session.user == "Administrator":
		return True

	if is_website_user():
		return False

	return True


def require_user_permission(doctype: str, name) -> None:
	if not _is_within_user_permissions(doctype, name):
		_refuse()


def _is_within_user_permissions(doctype: str, name) -> bool:
	from frappe.permissions import has_user_permission

	name = cstr(name)
	if not name:
		return False
	saved_messages = frappe.get_message_log()
	frappe.clear_messages()
	try:
		return has_user_permission(frappe.get_doc(doctype, name), frappe.session.user)
	except frappe.DoesNotExistError:
		return False
	finally:
		frappe.local.message_log = saved_messages


def require_permission(doctype: str, name, ptype: str = "read") -> None:
	if not _is_permitted(doctype, name, ptype):
		_refuse()


def require_party_permission(party_type: str | None, party) -> None:
	party = cstr(party)
	if not party:
		return
	party_type = cstr(party_type)
	if not frappe.db.exists("Party Type", party_type):
		_refuse()
	ptype = "select" if frappe.only_has_select_perm(party_type) else "read"
	if frappe.has_permission(party_type, ptype, doc=party):
		return
	if ptype != "select" or not frappe.has_permission(party_type, "read", doc=party):
		_refuse()


def _is_permitted(doctype: str, name, ptype: str) -> bool:
	name = cstr(name)
	if not name:
		return False
	saved_messages = frappe.get_message_log()
	frappe.clear_messages()
	try:
		if frappe.has_permission(doctype, ptype, doc=name):
			return True
		# v15 frappe has no select-implies-read fallback, so read must satisfy select here
		if ptype != "select":
			return False
		return frappe.has_permission(doctype, "read", doc=name)
	except frappe.DoesNotExistError:
		return False
	finally:
		frappe.local.message_log = saved_messages


def _refuse() -> None:
	frappe.flags.disable_traceback = True
	frappe.throw(frappe._("Not permitted"), frappe.PermissionError)
