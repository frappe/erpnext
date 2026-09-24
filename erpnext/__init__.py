import functools
import inspect
from typing import TypeVar

import frappe

__version__ = "17.0.0-dev"


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
	from frappe.utils.user import is_website_user

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

	from frappe.model.document import Document

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


def get_writable_vouchers(vouchers) -> set:
	"""Of `vouchers`, given as (doctype, name) pairs, the ones this user may write.

	get_list narrows the batch to readable names in one query per doctype -- names the caller
	cannot read at all, or that do not exist, cost nothing beyond that. Each surviving name is
	then confirmed individually, because no list query can stand in for the record-level check:
	has_user_permission() walks `doc.get_all_children()` and applies User Permissions to every
	child row's link fields, while permission query conditions only ever touch the parent table.
	A voucher readable at parent level whose item row points at a fenced warehouse is admitted by
	one and refused by the other.

	Returning the writable pairs keeps it fail-closed -- a voucher missing a doctype or a name is
	simply absent from the set.
	"""
	by_doctype = {}
	for doctype, name in vouchers:
		if doctype and name:
			by_doctype.setdefault(doctype, set()).add(name)

	writable = set()
	for doctype, names in by_doctype.items():
		try:
			readable = names & set(
				frappe.get_list(doctype, filters={"name": ("in", list(names))}, pluck="name")
			)
		except frappe.PermissionError:
			continue

		writable.update(
			(doctype, name) for name in readable if frappe.has_permission(doctype, ptype="write", doc=name)
		)

	return writable


def require_user_permission(doctype: str, name: str | int | None) -> None:
	"""Raise PermissionError unless the caller's User Permissions admit the named record.

	This enforces the fence only -- it does not ask whether the caller's roles grant `doctype`.
	Use it where the entitlement to call something lives on a different doctype from the record
	it reads: Quick Stock Balance is readable by Stock User, Stock Manager and System Manager,
	but warehouse.json ships a row for only the first of those, so gating on Warehouse would
	refuse a caller the page itself admits. What separates one caller's stock from another's
	there is the User Permission, and has_user_permission() is exactly that -- frappe's own
	link-field walk, the one has_permission() runs after its role check. It walks the record's
	links too, so a fence on Item Group still catches an Item outside it.
	"""
	from frappe.permissions import has_user_permission

	_refuse_unless(lambda: has_user_permission(frappe.get_doc(doctype, name), frappe.session.user), name)


def require_permission(doctype: str, name: str | int | None, ptype: str = "read") -> None:
	"""Raise PermissionError unless the caller may `ptype` the named record.

	`throw` is left at its default, which is what keeps the refusal quiet: frappe forwards
	print_logs=throw, and on a User Permission miss the log it would otherwise msgprint names
	the field and the value it tripped on -- "linked to Warehouse 'Goods In Transit - CFC' in
	row 1" -- describing a record the caller was just told it may not see.
	"""
	_refuse_unless(lambda: frappe.has_permission(doctype, ptype, doc=name), name)


def _refuse_unless(check, name) -> None:
	"""Run `check` behind detached logs; raise PermissionError unless it returns truthy.

	Every rejected input leaves by this one path, so a name that is forbidden, one that does not
	resolve and one that is empty are indistinguishable -- same exception, same message log, same
	disable_traceback. Left alone they are three different exits:

	- An empty name is falsy, and has_permission() with a falsy `doc` answers at DOCTYPE level,
	  which is True for anyone holding the doctype. Testing bool(name) first is what stops a
	  caller passing the guard by omitting the argument.
	- An absent name reaches get_doc(), which msgprints "<doctype> <name> not found" BEFORE
	  raising, and print_logs does not reach that call. Swapping message_log drops it.
	- has_permission_check_logs is appended to by push_perm_check_log whenever it is not None, so
	  an enclosing has_permission(print_logs=True) would collect this guard's refusal, naming the
	  record in someone else's response. Nulling it for the duration keeps it out.

	Both logs are restored, so a caller's own earlier messages and its in-progress collection
	survive a refusal.
	"""
	_message_log = frappe.local.message_log
	_check_logs = frappe.flags.get("has_permission_check_logs")
	frappe.local.message_log = []
	frappe.flags.has_permission_check_logs = None
	try:
		allowed = bool(name) and check()
	except frappe.DoesNotExistError:
		allowed = False
	finally:
		frappe.local.message_log = _message_log
		frappe.flags.has_permission_check_logs = _check_logs

	if not allowed:
		# throw() does not touch disable_traceback -- it is set in only two places in frappe, one
		# of which is check_doctype_permission, which this no longer calls. So set it here, or the
		# refusal carries a traceback into the response for a system user.
		frappe.flags.disable_traceback = True

		# frappe's own constant-message refusal, rather than a bare raise: a legitimate caller
		# gets something readable and every refusal still carries the SAME message. It must stay
		# constant -- naming the doctype would disclose it, and `doctype` is not always the
		# caller's own word for it. validate_child_row_is_writable() passes a parenttype read off
		# the database, so on a child table shared between parents an interpolated message would
		# name a parent doctype the caller never mentioned.
		frappe.throw_permission_error()
