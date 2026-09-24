import functools
import inspect
from typing import TypeVar

import frappe
from frappe.model.document import Document
from frappe.utils.messages import throw_permission_error
from frappe.utils.user import is_website_user

__version__ = "16.26.2"


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
		company = "_Test Company" if frappe.in_test else get_default_company()

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
		company = "_Test Company" if frappe.in_test else get_default_company()

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


T = TypeVar("T")


def normalize_ctx_input(T: type) -> callable:
	"""
	Normalizes the first argument (ctx) of the decorated function by:
	- Converting Document objects to dictionaries
	- Parsing JSON strings
	- Casting the result to the specified type T
	"""

	def decorator(func: callable):
		# conserve annotations for frappe.utils.typing_validations
		@functools.wraps(
			func,
			assigned=(
				a for a in functools.WRAPPER_ASSIGNMENTS if a not in ("__annotations__", "__annotate__")
			),
		)
		def wrapper(ctx: T | Document | dict | str, *args, **kwargs):
			if isinstance(ctx, Document):
				ctx = T(**ctx.as_dict())
			elif isinstance(ctx, dict):
				ctx = T(**ctx)
			else:
				ctx = T(**frappe.parse_json(ctx))

			return func(ctx, *args, **kwargs)

		# set annotations from function
		wrapper.__annotations__.update({k: v for k, v in func.__annotations__.items() if k != "ctx"})
		return wrapper

	return decorator


def _permitted(check) -> bool:
	"""Run `check` with frappe's own reporting suppressed, treating an absent record as refused.

	Two things have to be swallowed. has_permission reports through push_perm_check_log, which
	is inert only while nothing is collecting -- an enclosing has_permission(print_logs=True) IS
	collecting, and the record-derived text would land in that caller's log. And resolving a
	string name goes through get_doc, which msgprints "<doctype> <name> not found" BEFORE it
	raises, so the absence is already in the message log by the time we refuse. Swap both and
	restore whatever was there, so an absent name and a forbidden one are indistinguishable.
	"""
	_message_log = frappe.local.message_log
	_check_logs = frappe.flags.get("has_permission_check_logs")
	frappe.local.message_log = []
	frappe.flags["has_permission_check_logs"] = None
	try:
		return bool(check())
	except frappe.DoesNotExistError:
		return False
	finally:
		frappe.local.message_log = _message_log
		frappe.flags["has_permission_check_logs"] = _check_logs


def _refuse() -> None:
	"""The single refusal, so the two helpers cannot drift apart in how they deny."""
	# frappe sets this inside its own throw path, which we are deliberately not using.
	frappe.flags.disable_traceback = True
	# frappe's own constant: `throw(_("Not permitted"), frappe.PermissionError)`. A constant
	# cannot carry record data, and calling theirs means the message and the exception cannot
	# drift from frappe's. Do not interpolate -- the doctype is not always the caller's own:
	# validate_child_row_is_writable() passes a parenttype resolved from the database.
	throw_permission_error()


def require_permission(doctype: str, name: str | int | None, ptype: str = "read") -> None:
	"""Raise PermissionError unless the caller may `ptype` the named record.

	`frappe.has_permission` is called WITHOUT `throw`, which is what keeps the refusal quiet:
	the wrapper forwards `print_logs=throw`, so with throw set frappe msgprints the permission
	check log. On a User Permission miss that log is built from the record itself -- "linked to
	Warehouse 'Goods In Transit - CFC' in row 1" -- so a caller who may not read the record is
	told what is on it. Asking without throw collects nothing and we refuse here instead.

	`name` is tested before the call because it is NOT redundant: has_permission treats a falsy
	doc as absent and answers at doctype level, so an omitted name would be ALLOWED for anyone
	holding the doctype.

	The cost is that an entitled caller who mistypes a name is told "not permitted" rather than
	"not found" -- the same answer an unentitled one gets, which is the point.
	"""
	if not (name and _permitted(lambda: frappe.has_permission(doctype, ptype, doc=name))):
		_refuse()


def require_user_permission(doctype: str, name: str | int | None) -> None:
	"""Apply the caller's User Permissions to `name` without requiring DocPerm rights on it.

	For an endpoint whose callers are not expected to hold the record in their own right,
	require_permission() is too strong. Quick Stock Balance is granted to exactly Stock Manager,
	Stock User and System Manager, but Warehouse ships no DocPerm row for Stock Manager, so
	authorising the Warehouse outright denies a role the feature exists for -- measured.

	What is missing on those endpoints is the User Permission fence, so apply that and only
	that. `has_user_permission()` is the walk `has_permission()` performs after its role check:
	the record itself, then every link field on it and on its child rows. That breadth is the
	point -- an Item carrying a fenced Item Group is caught, where a fence keyed on the Item
	alone would miss it.

	Refuses exactly as require_permission() does, so the two are indistinguishable to a caller.
	"""
	# a `from` import binds only this name, leaving `frappe` the module-level global
	from frappe.permissions import has_user_permission

	if not (name and _permitted(lambda: has_user_permission(frappe.get_doc(doctype, name)))):
		_refuse()
