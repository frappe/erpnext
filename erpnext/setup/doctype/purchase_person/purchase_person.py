# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from collections import defaultdict
from itertools import chain

import frappe
from frappe import _
from frappe.query_builder import Interval
from frappe.query_builder.functions import Count, CurDate, UnixTimestamp
from frappe.utils import flt
from frappe.utils.nestedset import NestedSet, get_root_of

from erpnext import get_default_currency


class PurchasePerson(NestedSet):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.setup.doctype.target_detail.target_detail import TargetDetail

		commission_rate: DF.Data | None
		department: DF.Link | None
		employee: DF.Link | None
		enabled: DF.Check
		is_group: DF.Check
		lft: DF.Int
		old_parent: DF.Data | None
		parent_purchase_person: DF.Link | None
		purchase_person_name: DF.Data
		rgt: DF.Int
		targets: DF.Table[TargetDetail]
	# end: auto-generated types

	nsm_parent_field = "parent_purchase_person"

	def validate(self):
		if not self.enabled:
			self.validate_purchase_person()

		if not self.parent_purchase_person:
			self.parent_purchase_person = get_root_of("Purchase Person")

		for d in self.get("targets") or []:
			if not flt(d.target_qty) and not flt(d.target_amount):
				frappe.throw(_("Either target qty or target amount is mandatory."))
		self.validate_employee_id()

	def onload(self):
		self.load_dashboard_info()

	def load_dashboard_info(self):
		company_default_currency = get_default_currency()

		allocated_amount_against_order = flt(
			frappe.db.get_value(
				"Purchase Team",
				{
					"docstatus": 1,
					"parenttype": "Purchase Order",
					"purchase_person": self.purchase_person_name,
				},
				[{"SUM": "allocated_amount"}],
			)
		)

		allocated_amount_against_invoice = flt(
			frappe.db.get_value(
				"Purchase Team",
				{
					"docstatus": 1,
					"parenttype": "Purchase Invoice",
					"purchase_person": self.purchase_person_name,
				},
				[{"SUM": "allocated_amount"}],
			)
		)

		info = {}
		info["allocated_amount_against_order"] = allocated_amount_against_order
		info["allocated_amount_against_invoice"] = allocated_amount_against_invoice
		info["currency"] = company_default_currency

		self.set_onload("dashboard_info", info)

	def on_update(self):
		super().on_update()
		self.validate_one_root()

	def validate_purchase_person(self):
		purchase_team = frappe.qb.DocType("Purchase Team")

		query = (
			frappe.qb.from_(purchase_team)
			.select(purchase_team.purchase_person)
			.where(purchase_team.purchase_person == self.name)
			.groupby(purchase_team.purchase_person)
		).run(as_dict=True)

		if query:
			frappe.throw(_("The Purchase Person {0} is linked with existing transactions.").format(self.name))

	def validate_employee_id(self):
		if self.employee:
			purchase_person = frappe.db.get_value("Purchase Person", {"employee": self.employee})

			if purchase_person and purchase_person != self.name:
				frappe.throw(
					_("Another Purchase Person {0} exists with the same Employee id").format(purchase_person)
				)


def on_doctype_update():
	frappe.db.add_index("Purchase Person", ["lft", "rgt"])


def get_timeline_data(doctype: str, name: str) -> dict[int, int]:
	def _fetch_activity(doctype: str, date_field: str):
		purchase_team = frappe.qb.DocType("Purchase Team")
		transaction = frappe.qb.DocType(doctype)

		return dict(
			frappe.qb.from_(transaction)
			.join(purchase_team)
			.on(transaction.name == purchase_team.parent)
			.select(UnixTimestamp(transaction[date_field]), Count("*"))
			.where(purchase_team.purchase_person == name)
			.where(transaction[date_field] > CurDate() - Interval(years=1))
			.groupby(transaction[date_field])
			.run()
		)

	purchase_order_activity = _fetch_activity("Purchase Order", "transaction_date")
	purchase_invoice_activity = _fetch_activity("Purchase Invoice", "posting_date")

	merged_activities = defaultdict(int)

	for ts, count in chain(purchase_order_activity.items(), purchase_invoice_activity.items()):
		merged_activities[ts] += count

	return merged_activities
