# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.utils import cint, get_link_to_form

from erpnext.controllers.status_updater import StatusUpdater


class POSOpeningEntry(StatusUpdater):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.pos_opening_entry_detail.pos_opening_entry_detail import (
			POSOpeningEntryDetail,
		)

		amended_from: DF.Link | None
		balance_details: DF.Table[POSOpeningEntryDetail]
		company: DF.Link
		period_end_date: DF.Date | None
		period_start_date: DF.Datetime
		pos_closing_entry: DF.Data | None
		pos_profile: DF.Link
		posting_date: DF.Date
		set_posting_date: DF.Check
		status: DF.Literal["Draft", "Open", "Closed", "Cancelled"]
		user: DF.Link
	# end: auto-generated types

	def validate(self):
		self.validate_pos_profile_and_cashier()
		self.check_open_pos_exists()
		self.check_user_already_assigned()
		self.validate_payment_method_account()
		self.set_status()

	def validate_pos_profile_and_cashier(self):
		if not frappe.db.exists("POS Profile", self.pos_profile):
			frappe.throw(_("POS Profile {} does not exist.").format(self.pos_profile))

		pos_profile_company, pos_profile_disabled = frappe.db.get_value(
			"POS Profile", self.pos_profile, ["company", "disabled"]
		)

		if pos_profile_disabled:
			frappe.throw(_("POS Profile {} is disabled.").format(frappe.bold(self.pos_profile)))

		if self.company != pos_profile_company:
			frappe.throw(
				_("POS Profile {} does not belong to company {}").format(self.pos_profile, self.company)
			)

		if not cint(frappe.db.get_value("User", self.user, "enabled")):
			frappe.throw(_("User {} is disabled. Please select valid user/cashier").format(self.user))

	def check_open_pos_exists(self):
		if frappe.db.exists("POS Opening Entry", {"pos_profile": self.pos_profile, "status": "Open"}):
			frappe.throw(
				title=_("POS Opening Entry Exists"),
				msg=_(
					"{0} is open. Close the POS or cancel the existing POS Opening Entry to create a new POS Opening Entry."
				).format(frappe.bold(self.pos_profile)),
			)

	def check_user_already_assigned(self):
		if frappe.db.exists("POS Opening Entry", {"user": self.user, "status": "Open"}):
			frappe.throw(
				title=_("Cannot Assign Cashier"),
				msg=_("Cashier is currently assigned to another POS."),
			)

	def validate_payment_method_account(self):
		invalid_modes = []
		for d in self.balance_details:
			if d.mode_of_payment:
				account = frappe.db.get_value(
					"Mode of Payment Account",
					{"parent": d.mode_of_payment, "company": self.company},
					"default_account",
				)
				if not account:
					invalid_modes.append(get_link_to_form("Mode of Payment", d.mode_of_payment))

		if invalid_modes:
			if invalid_modes == 1:
				msg = _("Please set default Cash or Bank account in Mode of Payment {}")
			else:
				msg = _("Please set default Cash or Bank account in Mode of Payments {}")
			frappe.throw(msg.format(", ".join(invalid_modes)), title=_("Missing Account"))

	def on_submit(self):
		self.set_status(update=True)

	def before_cancel(self):
		self.check_poe_is_cancellable()

	def on_cancel(self):
		self.set_status(update=True)
		frappe.publish_realtime(
			f"poe_{self.name}",
			message={"operation": "Cancelled"},
			docname=f"POS Opening Entry/{self.name}",
		)

	def check_poe_is_cancellable(self):
		from erpnext.accounts.doctype.pos_closing_entry.pos_closing_entry import get_invoices

		invoices = get_invoices(
			self.period_start_date, frappe.utils.get_datetime(), self.pos_profile, self.user
		)
		if invoices.get("invoices"):
			frappe.throw(
				title=_("POS Opening Entry Cancellation Error"),
				msg=_("POS Opening Entry cannot be cancelled as unconsolidated Invoices exists."),
			)
