# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""The server half of the `Default Company` navigation item kind.

Optional, and here because this kind needs it: `permission_rule` on the type record is
`Custom`, so the framework hands every item of the kind to `can_see` and takes the list
it returns (`frappe/shell/navigation_filter.py`). The path is named in `hooks.py` under
`navigation_item_resolvers`, keyed by the type name; the framework appends `.can_see`.

It sits beside the record and the renderer rather than in a navigation module of its
own, because a kind is one contribution and not a scattering across three folders.
"""

from typing import TYPE_CHECKING

import frappe

if TYPE_CHECKING:
	from frappe.shell.navigation_filter import NavigationContext


def default_company() -> str | None:
	"""The same key the renderer reads out of `boot.sysdefaults`, so the item cannot be
	filtered against one company and then drawn pointing at another."""
	return frappe.defaults.get_defaults().get("company")


def can_see(items: list[dict], context: "NavigationContext") -> list[dict]:
	"""Which of these items this user may follow.

	`Custom` rather than `Readable DocType`, and that is the whole reason the kind carries
	server code at all. The item points at one company *document*, and restricting a user
	to a subset of companies with `User Permission` is ordinary on an ERPNext site -- so
	the doctype-level bucket would leave the item on the rail for somebody whose only
	company is a different one. frappe/frappe#42231 accepted that leak for `Record` items
	and wrote it down as a cost; a kind with exactly one destination can afford the honest
	check instead.

	One permission call for the batch rather than one per item. Every item of this kind
	shares the site's default company, so there is one question to ask however many rows
	name it -- which is what the batched signature is for (frappe/frappe#42231 measured 553
	per-item checks at 3,594 ms against 25 ms for a single pass, inside boot's blocking
	fetch).
	"""
	company = default_company()

	# Nothing to point at. Dropped here rather than left for the renderer so the row stays
	# out of boot entirely, instead of being sent and then declined by the browser.
	if not company:
		return []

	try:
		permitted = frappe.has_permission("Company", doc=company, user=context.user)
	except frappe.DoesNotExistError:
		# Global Defaults naming a company somebody has since deleted. Left to raise, the
		# framework catches it, fails the kind closed and writes one Error Log -- and it would
		# write another on the next boot, and on every other person's, because the cause is a
		# site's data rather than a passing fault. It is the same "nothing to point at" as an
		# unfinished setup wizard, so it is answered the same way.
		#
		# Caught rather than checked ahead of time: `has_permission` already loads the document
		# (lazily, without child tables), so an existence check would be a second query on every
		# boot to save one on almost none.
		return []

	return items if permitted else []
