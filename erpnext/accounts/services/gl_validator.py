# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""List-level validations for a GL map.

These functions assert that an assembled list of GL entries is legal to post —
no disabled accounts, the period/freeze/PCV gates pass, dimensions are allowed.
They do not mutate or repair the entries; balancing and round-off live with the
posting sink in ``erpnext.accounts.general_ledger``.
"""

import frappe
from frappe import _
from frappe.utils import cint, formatdate, getdate

from erpnext.accounts.doctype.accounting_period.accounting_period import ClosedAccountingPeriod
from erpnext.exceptions import InvalidAccountDimensionError, MandatoryAccountDimensionError


def validate_disabled_accounts(gl_map):
	accounts = [d.account for d in gl_map if d.account]

	disabled_accounts = frappe.get_all(
		"Account",
		filters={"disabled": 1, "is_group": 0, "company": gl_map[0].company},
		fields=["name"],
	)

	used_disabled_accounts = set(accounts).intersection(set([d.name for d in disabled_accounts]))
	if used_disabled_accounts:
		account_list = "<br>"
		account_list += ", ".join([frappe.bold(d) for d in used_disabled_accounts])
		frappe.throw(
			_("Cannot create accounting entries against disabled accounts: {0}").format(account_list),
			title=_("Disabled Account Selected"),
		)


def validate_accounting_period(gl_map):
	accounting_periods = frappe.db.sql(
		""" SELECT
			ap.name as name, ap.exempted_role as exempted_role
		FROM
			`tabAccounting Period` ap, `tabClosed Document` cd
		WHERE
			ap.name = cd.parent
			AND ap.company = %(company)s
			AND ap.disabled = 0
			AND cd.closed = 1
			AND cd.document_type = %(voucher_type)s
			AND %(date)s between ap.start_date and ap.end_date
			""",
		{
			"date": gl_map[0].posting_date,
			"company": gl_map[0].company,
			"voucher_type": gl_map[0].voucher_type,
		},
		as_dict=1,
	)

	if accounting_periods:
		if accounting_periods[0].exempted_role:
			exempted_roles = accounting_periods[0].exempted_role
			if exempted_roles in frappe.get_roles():
				return
		frappe.throw(
			_(
				"You cannot create or cancel any accounting entries with in the closed Accounting Period {0}"
			).format(frappe.bold(accounting_periods[0].name)),
			ClosedAccountingPeriod,
		)


def validate_cwip_accounts(gl_map):
	"""Validate that CWIP account are not used in Journal Entry"""
	if gl_map and gl_map[0].voucher_type != "Journal Entry":
		return

	cwip_enabled = any(
		cint(ac.enable_cwip_accounting)
		for ac in frappe.db.get_all("Asset Category", "enable_cwip_accounting")
	)
	if cwip_enabled:
		cwip_accounts = [
			d[0]
			for d in frappe.db.sql(
				"""select name from tabAccount
			where account_type = 'Capital Work in Progress' and is_group=0"""
			)
		]

		for entry in gl_map:
			if entry.account in cwip_accounts:
				frappe.throw(
					_(
						"Account: <b>{0}</b> is capital Work in progress and can not be updated by Journal Entry"
					).format(entry.account)
				)


def check_freezing_date(posting_date, company, adv_adj=False):
	"""
	Nobody can do GL Entries where posting date is before freezing date
	except authorized person

	Administrator has all the roles so this check will be bypassed if any role is allowed to post
	Hence stop admin to bypass if accounts are freezed
	"""
	if not adv_adj:
		acc_frozen_till_date = frappe.db.get_value("Company", company, "accounts_frozen_till_date")
		if acc_frozen_till_date:
			frozen_accounts_modifier = frappe.db.get_value(
				"Company", company, "role_allowed_for_frozen_entries"
			)
			if getdate(posting_date) <= getdate(acc_frozen_till_date) and (
				frozen_accounts_modifier not in frappe.get_roles() or frappe.session.user == "Administrator"
			):
				frappe.throw(
					_("You are not authorized to add or update entries before {0}").format(
						formatdate(acc_frozen_till_date)
					)
				)


def validate_against_pcv(is_opening, posting_date, company):
	if is_opening and frappe.db.exists("Period Closing Voucher", {"docstatus": 1, "company": company}):
		frappe.throw(
			_("Opening Entry can not be created after Period Closing Voucher is created."),
			title=_("Invalid Opening Entry"),
		)

	last_pcv_date = frappe.db.get_value(
		"Period Closing Voucher", {"docstatus": 1, "company": company}, [{"MAX": "period_end_date"}]
	)

	if last_pcv_date and getdate(posting_date) <= getdate(last_pcv_date):
		message = _("Books have been closed till the period ending on {0}").format(formatdate(last_pcv_date))
		message += "</br >"
		message += _("You cannot create/amend any accounting entries till this date.")
		frappe.throw(message, title=_("Period Closed"))


def validate_allowed_dimensions(gl_entry, dimension_filter_map):
	for key, value in dimension_filter_map.items():
		dimension = key[0]
		account = key[1]

		if gl_entry.account == account:
			if value["is_mandatory"] and not gl_entry.get(dimension):
				frappe.throw(
					_("{0} is mandatory for account {1}").format(
						frappe.bold(frappe.unscrub(dimension)), frappe.bold(gl_entry.account)
					),
					MandatoryAccountDimensionError,
				)

			if value["allow_or_restrict"] == "Allow":
				if gl_entry.get(dimension) and gl_entry.get(dimension) not in value["allowed_dimensions"]:
					frappe.throw(
						_("Invalid value {0} for {1} against account {2}").format(
							frappe.bold(gl_entry.get(dimension)),
							frappe.bold(frappe.unscrub(dimension)),
							frappe.bold(gl_entry.account),
						),
						InvalidAccountDimensionError,
					)
			else:
				if gl_entry.get(dimension) and gl_entry.get(dimension) in value["allowed_dimensions"]:
					frappe.throw(
						_("Invalid value {0} for {1} against account {2}").format(
							frappe.bold(gl_entry.get(dimension)),
							frappe.bold(frappe.unscrub(dimension)),
							frappe.bold(gl_entry.account),
						),
						InvalidAccountDimensionError,
					)
