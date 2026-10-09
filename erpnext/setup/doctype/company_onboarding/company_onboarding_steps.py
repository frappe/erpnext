# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
"""The steps of Company Onboarding.

A step is a function that gets the Company Onboarding document and returns its title,
description, and whether it is done. "Done" always comes from the company's data, never from a
click.

Every app, ERPNext included, lists its steps in hooks.py. A step can say where it goes, before or
after another step by its name (the last part of its path)::

    company_onboarding_steps = [
        {"step": "india_compliance.onboarding.gst_settings", "after": "chart_of_accounts"},
        "hrms.onboarding.add_employees",  # no place given: just before Go Live
    ]

Two steps asking for the same place keep the order of the apps' install. A step whose place is
not found goes just before Go Live, and Go Live is always last.
"""

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt

HOOK_NAME = "company_onboarding_steps"
# Go Live always comes last, whatever the hooks say
LAST_STEP = "erpnext.setup.doctype.company_onboarding.company_onboarding_steps.go_live"


def get_step_paths() -> list[str]:
	"""Every app's steps, in the order the user sees them."""
	steps = []
	added = {}  # place -> how many steps were put after it, so the earlier app stays first
	pending = get_hooked_steps()

	# a step may point to a step that is added later, so keep going while steps find their place
	while pending:
		waiting = []
		for entry in pending:
			place = entry.get("after") or entry.get("before")
			index = find_step(steps, place) if place else None
			if index is None and place and find_step(pending, place, key="step") is not None:
				waiting.append(entry)
			elif index is None:
				steps.append(entry["step"])
			elif entry.get("after"):
				count = added.get(steps[index], 0)
				added[steps[index]] = count + 1
				steps.insert(index + 1 + count, entry["step"])
			else:
				steps.insert(index, entry["step"])
		if len(waiting) == len(pending):
			# they only point at each other, so none can be placed: put them before Go Live
			steps.extend(entry["step"] for entry in waiting)
			break
		pending = waiting

	return [*steps, LAST_STEP]


def get_hooked_steps() -> list[dict]:
	"""Steps from the hook of every installed app, in install order. Bad entries are skipped."""
	entries = []
	for app in frappe.get_installed_apps():
		for entry in frappe.get_hooks(HOOK_NAME, app_name=app) or []:
			if isinstance(entry, str):
				entry = {"step": entry}
			if not isinstance(entry, dict) or not isinstance(entry.get("step"), str):
				frappe.logger("company_onboarding").warning(f"Skipping step {entry!r} from {app}")
				continue
			if is_last_step(entry["step"]):
				continue
			if is_last_step(entry.get("after")):
				# nothing comes after Go Live
				entry = {"step": entry["step"], "before": "go_live"}
			if is_last_step(entry.get("before")):
				entry = {"step": entry["step"]}
			entries.append(entry)
	return entries


def find_step(steps: list, name: str, key: str | None = None) -> int | None:
	"""Where a step is in the list, by its full path or its name (the last part of the path)."""
	for index, step in enumerate(steps):
		path = step[key] if key else step
		if name in (path, path.rsplit(".", 1)[-1]):
			return index
	return None


def is_last_step(name: str | None) -> bool:
	return bool(name) and name in (LAST_STEP, LAST_STEP.rsplit(".", 1)[-1])


def chart_of_accounts(onboarding) -> dict:
	if onboarding.chart_of_accounts_source == "Existing":
		description = _("You kept the chart made during setup. You can still change accounts later.")
	elif onboarding.chart_of_accounts_source == "Imported":
		description = _("You imported your own chart. You can still change accounts later.")
	else:
		description = _("Keep the chart made during setup, or import your own.")
	return {
		"title": _("Chart of Accounts"),
		"description": description,
		"done": bool(onboarding.chart_of_accounts_source),
	}


def opening_balances(onboarding) -> dict:
	return {
		"title": _("Opening balances"),
		"description": _("Bring the closing balances from your old books. Type them in, or upload a sheet."),
		"done": all_opening_balances_posted(onboarding),
	}


def review(onboarding) -> dict:
	return {
		"title": _("Review"),
		"description": _(
			"Compare the Balance Sheet and Profit and Loss with your old books. Temporary Opening should be zero."
		),
		"done": all_opening_balances_posted(onboarding)
		and not get_temporary_opening_balance(onboarding.company),
	}


def go_live(onboarding) -> dict:
	return {
		"title": _("Go Live"),
		"description": _("Start using ERPNext for this company."),
		"done": onboarding.status == "Live",
	}


def all_opening_balances_posted(onboarding) -> bool:
	rows = onboarding.opening_balances
	return bool(rows) and all(row.status == "Posted" for row in rows)


def get_temporary_opening_balance(company: str) -> float:
	"""Debit minus credit on the company's Temporary accounts. Zero once the opening is complete."""
	accounts = frappe.get_all(
		"Account", filters={"company": company, "account_type": "Temporary", "is_group": 0}, pluck="name"
	)
	if not accounts:
		return 0.0

	gle = frappe.qb.DocType("GL Entry")
	balance = (
		frappe.qb.from_(gle)
		.select(Sum(gle.debit) - Sum(gle.credit))
		.where(gle.account.isin(accounts) & (gle.is_cancelled == 0))
	).run()[0][0]
	return flt(balance)
