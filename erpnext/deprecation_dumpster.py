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


@deprecated(
	"erpnext.projects.doctype.project_update.project_update.daily_reminder",
	"2026-10-05",
	"v18",
	"Not used anymore. Projects collect progress through Collect Progress on the Project.",
)
def project_update_daily_reminder():
	import frappe
	from frappe.utils import add_days, today

	frappe.only_for("Projects Manager")

	holiday_today = frappe.db.exists("Holiday", {"holiday_date": today()})

	projects = frappe.get_all(
		"Project",
		fields=[
			"name",
			"project_name",
			"frequency",
			"expected_start_date",
			"expected_end_date",
			"percent_complete",
		],
		limit_page_length=0,
	)
	for project in projects:
		project_id = project.name
		frequency = project.frequency
		date_start = project.expected_start_date
		date_end = project.expected_end_date
		progress = project.percent_complete
		number_of_drafts = frappe.db.count("Project Update", {"project": project_id, "docstatus": 0})
		update = frappe.get_all(
			"Project Update",
			filters={"project": project_id, "date": add_days(today(), -1)},
			fields=["name", "date", "time"],
			as_list=True,
		)
		project_update_email_sending(
			project_id,
			project.project_name,
			frequency,
			date_start,
			date_end,
			progress,
			number_of_drafts,
			update,
			holiday_today,
		)


@deprecated(
	"erpnext.projects.doctype.project_update.project_update.email_sending",
	"2026-10-05",
	"v18",
	"Not used anymore.",
)
def project_update_email_sending(
	project_id,
	project_name,
	frequency,
	date_start,
	date_end,
	progress,
	number_of_drafts,
	update,
	holiday_today,
):
	import frappe

	msg = (
		"<p>Project Name: "
		+ project_name
		+ "</p><p>Frequency: "
		+ " "
		+ str(frequency)
		+ "</p><p>Update Reminder:"
		+ " "
		+ str(date_start)
		+ "</p><p>Expected Date End:"
		+ " "
		+ str(date_end)
		+ "</p><p>Percent Progress:"
		+ " "
		+ str(progress)
		+ "</p><p>Number of Updates:"
		+ " "
		+ str(len(update))
		+ "</p>"
		+ "</p><p>Number of drafts:"
		+ " "
		+ str(number_of_drafts)
		+ "</p>"
	)
	msg += """</u></b></p><table class='table table-bordered'><tr>
                <th>Project ID</th><th>Date Updated</th><th>Time Updated</th></tr>"""
	for updates in update:
		msg += (
			"<tr><td>"
			+ str(updates[0])
			+ "</td><td>"
			+ str(updates[1])
			+ "</td><td>"
			+ str(updates[2])
			+ "</td></tr>"
		)

	msg += "</table>"
	if not holiday_today:
		recipients = frappe.get_all(
			"Project User",
			filters={"parent": project_id},
			pluck="user",
			limit_page_length=0,
		)
		for user in recipients:
			frappe.sendmail(recipients=[user], subject=frappe._(project_name + " " + "Summary"), message=msg)
	else:
		pass
