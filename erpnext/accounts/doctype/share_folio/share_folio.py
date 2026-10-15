# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

from erpnext.accounts.shareholding.locking import lock_company


class ShareFolio(Document):
	def before_insert(self):
		if not (frappe.flags.get("creating_share_folio") or frappe.flags.get("in_patch")):
			frappe.throw(_("Share Folios are created automatically by Share Transactions."))

	def validate(self):
		lock_company(self.company)
		if not self.is_new() and not frappe.flags.get("in_patch"):
			frappe.throw(_("Share Folios cannot be edited directly."))

		# Preserve an explicitly supplied number during migration; otherwise use the
		# generated document name as the externally visible folio number.
		if not self.folio_number:
			self.folio_number = self.name

		self.validate_holder()
		self.validate_membership_dates()
		self.validate_uniqueness()

	def validate_holder(self):
		if self.is_treasury:
			self.shareholder = None
			self.date_of_becoming_member = None
			self.date_of_cessation = None
		elif not self.shareholder:
			frappe.throw(_("Shareholder is required for a non-treasury folio."))

	def validate_membership_dates(self):
		if (
			self.date_of_becoming_member
			and self.date_of_cessation
			and getdate(self.date_of_cessation) < getdate(self.date_of_becoming_member)
		):
			frappe.throw(_("Date of Cessation cannot be before Date of Becoming Member."))

	def validate_uniqueness(self):
		if frappe.db.exists(
			"Share Folio",
			{
				"company": self.company,
				"folio_number": self.folio_number,
				"name": ["!=", self.name],
			},
		):
			frappe.throw(
				_("Folio Number {0} already exists for company {1}.").format(
					frappe.bold(self.folio_number), frappe.bold(self.company)
				)
			)

		identity_filters = {
			"company": self.company,
			"is_treasury": 1 if self.is_treasury else 0,
			"name": ["!=", self.name],
		}
		if not self.is_treasury:
			identity_filters["shareholder"] = self.shareholder

		if frappe.db.exists("Share Folio", identity_filters):
			if self.is_treasury:
				frappe.throw(
					_("A treasury folio already exists for company {0}.").format(frappe.bold(self.company))
				)
			frappe.throw(
				_("A folio already exists for shareholder {0} in company {1}.").format(
					frappe.bold(self.shareholder), frappe.bold(self.company)
				)
			)

	def on_trash(self):
		if not frappe.flags.get("in_patch"):
			frappe.throw(_("Share Folios cannot be deleted directly."))


def on_doctype_update():
	frappe.db.add_unique(
		"Share Folio", ["company", "folio_number"], constraint_name="unique_share_folio_number_per_company"
	)
