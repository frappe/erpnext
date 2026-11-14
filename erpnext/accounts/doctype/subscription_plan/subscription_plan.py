# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import date

import frappe
from dateutil import relativedelta
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months, date_diff, get_link_to_form, getdate

from erpnext.utilities.product import get_price


class SubscriptionPlan(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		billing_interval: DF.Literal["Day", "Week", "Month", "Year"]
		billing_interval_count: DF.Int
		cost: DF.Currency
		cost_center: DF.Link | None
		currency: DF.Link
		item: DF.Link
		payment_gateway: DF.Link | None
		plan_name: DF.Data
		price_determination: DF.Literal["", "Fixed Rate", "Based On Price List", "Monthly Rate"]
		price_list: DF.Link | None
		product_price_id: DF.Data | None
	# end: auto-generated types

	def validate(self):
		self.validate_interval_count()
		self.validate_price_list()
		self.validate_interval_change()

	def validate_interval_count(self):
		if self.billing_interval_count < 1:
			frappe.throw(_("Billing Interval Count cannot be less than 1"))

	def validate_price_list(self):
		if self.price_determination == "Based On Price List" and not self.price_list:
			frappe.throw(_("Price List is required when the price is based on a price list"))

	def validate_interval_change(self):
		if self.is_new() or not (
			self.has_value_changed("billing_interval") or self.has_value_changed("billing_interval_count")
		):
			return

		# all plans in a subscription must share one billing cycle
		if subscriptions := self.get_subscriptions_with_other_plans():
			frappe.throw(
				_(
					"Cannot change the billing interval because these Subscriptions also use other plans: {0}"
				).format(", ".join(get_link_to_form("Subscription", name) for name in subscriptions))
			)

	def get_subscriptions_with_other_plans(self):
		plan_detail = frappe.qb.DocType("Subscription Plan Detail")
		other_plan_detail = frappe.qb.DocType("Subscription Plan Detail").as_("other_plan_detail")
		subscription = frappe.qb.DocType("Subscription")
		return (
			frappe.qb.from_(plan_detail)
			.join(subscription)
			.on(subscription.name == plan_detail.parent)
			.join(other_plan_detail)
			.on(
				(other_plan_detail.parent == plan_detail.parent)
				& (other_plan_detail.plan != plan_detail.plan)
			)
			.select(plan_detail.parent)
			.distinct()
			.where(
				(plan_detail.plan == self.name)
				& (plan_detail.parenttype == "Subscription")
				& subscription.status.notin(["Cancelled", "Completed"])
			)
			.run(pluck=True)
		)


@frappe.whitelist()
def get_plan_rate(
	plan: str,
	quantity: int = 1,
	customer: str | None = None,
	start_date: str | date | None = None,
	end_date: str | date | None = None,
	prorate_factor: float = 1,
	party: str | None = None,
):
	plan = frappe.get_doc("Subscription Plan", plan)
	plan.check_permission("read")
	if plan.price_determination == "Fixed Rate":
		return plan.cost * prorate_factor

	elif plan.price_determination == "Based On Price List":
		# Subscription passes its party, which may be a Supplier, as `customer`
		price = get_price_list_price(plan, quantity, customer or party)
		if not price:
			return 0
		else:
			return price.price_list_rate * prorate_factor

	elif plan.price_determination == "Monthly Rate":
		return plan.cost * get_months_in_period(getdate(start_date), getdate(end_date))


def get_price_list_price(plan, quantity, customer):
	party = customer_group = None
	if customer and frappe.db.exists("Customer", customer):
		party = frappe._dict(doctype="Customer", name=customer)
		customer_group = frappe.db.get_value("Customer", customer, "customer_group")

	return get_price(
		item_code=plan.item,
		price_list=plan.price_list,
		customer_group=customer_group,
		company=None,
		qty=quantity,
		party=party,
	)


def get_months_in_period(start_date, end_date):
	"""Months from start_date to end_date (both included). Days left over count as a part month."""
	period = relativedelta.relativedelta(add_days(end_date, 1), start_date)
	months = period.years * 12 + period.months
	if not period.days:
		return months

	if not frappe.db.get_single_value("Subscription Settings", "prorate"):
		return months + 1

	part_month_start = add_months(start_date, months)
	return months + period.days / date_diff(add_months(part_month_start, 1), part_month_start)
