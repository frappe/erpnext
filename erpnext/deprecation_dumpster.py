"""
Welcome to the Deprecation Dumpster: Where Old Code Goes to Party! 🎉🗑️

This file is the final resting place (or should we say, "retirement home"?) for all the deprecated functions and methods of the ERPNext app. It's like a code nursing home, but with more monkey-patching and less bingo.

Each function or method that checks in here comes with its own personalized decorator, complete with:
1. The date it was marked for deprecation (its "over the hill" birthday)
2. The ERPNext version at the beginning of which it becomes an error and at the end of which it will be removed (its "graduation" to the great codebase in the sky)
3. A user-facing note on alternative solutions (its "parting wisdom")

Warning: The global namespace herein is more patched up than a sailor's favorite pair of jeans. Proceed with caution and a sense of humor!

Remember, deprecated doesn't mean useless - it just means these functions are enjoying their golden years before their final bow. Treat them with respect, and maybe bring them some virtual prune juice.

Enjoy your stay in the Deprecation Dumpster, where every function gets a second chance to shine (or at least, to not break everything).
"""

import functools
import re
import sys
import warnings

from frappe.deprecation_dumpster import Color, _deprecated, colorize


# we use Warning because DeprecationWarning has python default filters which would exclude them from showing
# see also frappe.__init__ enabling them when a dev_server
class ERPNextDeprecationError(Warning):
	"""Deprecated feature in current version.

	Raises an error by default but can be configured via PYTHONWARNINGS in an emergency.
	"""


class ERPNextDeprecationWarning(Warning):
	"""Deprecated feature in next version"""


class PendingERPNextDeprecationWarning(ERPNextDeprecationWarning):
	"""Deprecated feature in develop beyond next version.

	Warning ignored by default.

	The deprecation decision may still be reverted or deferred at this stage.
	Regardless, using the new variant is encouraged and stable.
	"""


warnings.simplefilter("error", ERPNextDeprecationError)
warnings.simplefilter("ignore", PendingERPNextDeprecationWarning)


class V15ERPNextDeprecationWarning(ERPNextDeprecationError):
	pass


class V16ERPNextDeprecationWarning(ERPNextDeprecationWarning):
	pass


class V17ERPNextDeprecationWarning(PendingERPNextDeprecationWarning):
	pass


def __get_deprecation_class(graduation: str | None = None, class_name: str | None = None) -> type:
	if graduation:
		# Scrub the graduation string to ensure it's a valid class name
		cleaned_graduation = re.sub(r"\W|^(?=\d)", "_", graduation.upper())
		class_name = f"{cleaned_graduation}ERPNextDeprecationWarning"
		current_module = sys.modules[__name__]
	try:
		return getattr(current_module, class_name)
	except AttributeError:
		return PendingDeprecationWarning


def deprecated(original: str, marked: str, graduation: str, msg: str, stacklevel: int = 1):
	"""Decorator to wrap a function/method as deprecated.

	Arguments:
	        - original: frappe.utils.make_esc  (fully qualified)
	        - marked: 2024-09-13  (the date it has been marked)
	        - graduation: v17  (generally: current version + 2)
	        - msg: additional instructions
	"""

	def decorator(func):
		# Get the filename of the caller
		func.__name__ = original
		wrapper = _deprecated(
			colorize(f"It was marked on {marked} for removal from {graduation} with note: ", Color.RED)
			+ colorize(f"{msg}", Color.YELLOW),
			category=__get_deprecation_class(graduation),
			stacklevel=stacklevel,
		)

		return functools.update_wrapper(wrapper, func)(func)

	return decorator


def deprecation_warning(marked: str, graduation: str, msg: str):
	"""Warn in-place from a deprecated code path, for objects use `@deprecated` decorator from the deprectation_dumpster"

	Arguments:
	        - marked: 2024-09-13  (the date it has been marked)
	        - graduation: v17  (generally: current version + 2)
	        - msg: additional instructions
	"""

	warnings.warn(
		colorize(
			f"This codepath was marked (DATE: {marked}) deprecated"
			f" for removal (from {graduation} onwards); note:\n ",
			Color.RED,
		)
		+ colorize(f"{msg}\n", Color.YELLOW),
		category=__get_deprecation_class(graduation),
		stacklevel=2,
	)


### Party starts here
@deprecated(
	"erpnext.controllers.taxes_and_totals.get_itemised_taxable_amount",
	"2024-11-07",
	"v17",
	"The field item_wise_tax_detail now already contains the net_amount per tax.",
)
def taxes_and_totals_get_itemised_taxable_amount(items):
	import frappe

	itemised_taxable_amount = frappe._dict()
	for item in items:
		item_code = item.item_code or item.item_name
		itemised_taxable_amount.setdefault(item_code, 0)
		itemised_taxable_amount[item_code] += item.net_amount

	return itemised_taxable_amount


@deprecated(
	"erpnext.stock.get_pos_profile_item_details",
	"2024-11-19",
	"v16",
	"Use erpnext.stock.get_pos_profile_item_details_ with a flipped signature",
)
def get_pos_profile_item_details(company, ctx, pos_profile=None, update_data=False):
	from erpnext.stock.get_item_details import get_pos_profile_item_details_

	return get_pos_profile_item_details_(ctx, company, pos_profile=pos_profile, update_data=update_data)


@deprecated(
	"erpnext.stock.get_item_warehouse",
	"2024-11-19",
	"v16",
	"Use erpnext.stock.get_item_warehouse_ with a flipped signature",
)
def get_item_warehouse(item, ctx, overwrite_warehouse, defaults=None):
	from erpnext.stock.get_item_details import get_item_warehouse_

	return get_item_warehouse_(ctx, item, overwrite_warehouse, defaults=defaults)
