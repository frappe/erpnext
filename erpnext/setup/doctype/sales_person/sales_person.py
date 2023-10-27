# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
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


class SalesPerson(NestedSet):
	nsm_parent_field = "parent_sales_person"

	def before_validate(self):
		self.convert_commission_rate_to_float()

	def convert_commission_rate_to_float(self):
		# 'commission_rate' is a Data field. Due to the challenges in directly changing a field
		# type from 'Data' to 'Float' in the Frappe Framework, this workaround ensures that,
		# moving forward, the value is always a valid float.
		try:
			self.commission_rate = float(self.commission_rate)
		except ValueError:
			try:
				modified_value = self.commission_rate.replace(",", ".")
				self.commission_rate = float(modified_value)
			except ValueError:
				frappe.throw(
					_(
						"Commission Rate must be a number. Please avoid using characters other than digits and a decimal point."
					)
				)

	def validate(self):
		if not self.parent_sales_person:
			self.parent_sales_person = get_root_of("Sales Person")

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
				"Sales Team",
				{"docstatus": 1, "parenttype": "Sales Order", "sales_person": self.sales_person_name},
				"sum(allocated_amount)",
			)
		)

		allocated_amount_against_invoice = flt(
			frappe.db.get_value(
				"Sales Team",
				{"docstatus": 1, "parenttype": "Sales Invoice", "sales_person": self.sales_person_name},
				"sum(allocated_amount)",
			)
		)

		info = {}
		info["allocated_amount_against_order"] = allocated_amount_against_order
		info["allocated_amount_against_invoice"] = allocated_amount_against_invoice
		info["currency"] = company_default_currency

		self.set_onload("dashboard_info", info)

	def on_update(self):
		super(SalesPerson, self).on_update()
		self.validate_one_root()

	def get_email_id(self):
		if self.employee:
			user = frappe.db.get_value("Employee", self.employee, "user_id")
			if not user:
				frappe.throw(_("User ID not set for Employee {0}").format(self.employee))
			else:
				return frappe.db.get_value("User", user, "email") or user

	def validate_employee_id(self):
		if self.employee:
			sales_person = frappe.db.get_value("Sales Person", {"employee": self.employee})

			if sales_person and sales_person != self.name:
				frappe.throw(
					_("Another Sales Person {0} exists with the same Employee id").format(sales_person)
				)


def on_doctype_update():
	frappe.db.add_index("Sales Person", ["lft", "rgt"])


def get_timeline_data(doctype: str, name: str) -> dict[int, int]:
	def _fetch_activity(doctype: str, date_field: str):
		sales_team = frappe.qb.DocType("Sales Team")
		transaction = frappe.qb.DocType(doctype)

		return dict(
			frappe.qb.from_(transaction)
			.join(sales_team)
			.on(transaction.name == sales_team.parent)
			.select(UnixTimestamp(transaction[date_field]), Count("*"))
			.where(sales_team.sales_person == name)
			.where(transaction[date_field] > CurDate() - Interval(years=1))
			.groupby(transaction[date_field])
			.run()
		)

	sales_order_activity = _fetch_activity("Sales Order", "transaction_date")
	sales_invoice_activity = _fetch_activity("Sales Invoice", "posting_date")
	delivery_note_activity = _fetch_activity("Delivery Note", "posting_date")

	merged_activities = defaultdict(int)

	for ts, count in chain(
		sales_order_activity.items(), sales_invoice_activity.items(), delivery_note_activity.items()
	):
		merged_activities[ts] += count

	return merged_activities
