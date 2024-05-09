# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from datetime import date

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import (
	add_days,
	add_months,
	add_to_date,
	cint,
	date_diff,
	flt,
	get_last_day,
	get_link_to_form,
	getdate,
	nowdate,
)

from erpnext import get_default_company, get_default_cost_center
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
	get_accounting_dimensions,
)
from erpnext.accounts.doctype.subscription_plan.subscription_plan import get_plan_rate
from erpnext.accounts.party import get_party_account_currency


class InvoiceCancelled(frappe.ValidationError):
	pass


class InvoiceNotCancelled(frappe.ValidationError):
	pass


DateTimeLikeObject = str | date


class Subscription(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.subscription_plan_detail.subscription_plan_detail import (
			SubscriptionPlanDetail,
		)

		additional_discount_amount: DF.Currency
		additional_discount_percentage: DF.Percent
		apply_additional_discount: DF.Literal["", "Grand Total", "Net Total"]
		cancel_at_period_end: DF.Check
		cancelation_date: DF.Date | None
		company: DF.Link | None
		cost_center: DF.Link | None
		current_invoice_end: DF.Date | None
		current_invoice_start: DF.Date | None
		days_until_due: DF.Int
		end_date: DF.Date | None
		follow_calendar_months: DF.Check
		generate_invoice_at: DF.Literal[
			"End of the current subscription period",
			"Beginning of the current subscription period",
			"Days before the current subscription period",
		]
		generate_new_invoices_past_due_date: DF.Check
		number_of_days: DF.Int
		party: DF.DynamicLink
		party_type: DF.Link
		plans: DF.Table[SubscriptionPlanDetail]
		purchase_tax_template: DF.Link | None
		sales_tax_template: DF.Link | None
		start_date: DF.Date | None
		status: DF.Literal["", "Trialling", "Active", "Past Due Date", "Cancelled", "Unpaid", "Completed"]
		submit_invoice: DF.Check
		trial_period_end: DF.Date | None
		trial_period_start: DF.Date | None
	# end: auto-generated types

	def before_insert(self):
		# update start just before the subscription doc is created
		self.update_subscription_period(self.start_date)

	def update_subscription_period(self, date: DateTimeLikeObject | None = None):
		"""
		Subscription period is the period to be billed. This method updates the
		beginning of the billing period and end of the billing period.
		The beginning of the billing period is represented in the doctype as
		`current_invoice_start` and the end of the billing period is represented
		as `current_invoice_end`.
		"""
		self.current_invoice_start = self.get_current_invoice_start(date)
		self.current_invoice_end = self.get_current_invoice_end(self.current_invoice_start)

	def _get_subscription_period(self, date: DateTimeLikeObject | None = None):
		_current_invoice_start = self.get_current_invoice_start(date)
		_current_invoice_end = self.get_current_invoice_end(_current_invoice_start)

		return _current_invoice_start, _current_invoice_end

	def get_current_invoice_start(self, date: DateTimeLikeObject | None = None) -> DateTimeLikeObject:
		"""
		This returns the date of the beginning of the current billing period.
		If the `date` parameter is not given , it will be automatically set as today's
		date.
		"""
		_current_invoice_start = None

		if self.trial_period_end and getdate(self.trial_period_end) > getdate(self.start_date):
			_current_invoice_start = add_days(self.trial_period_end, 1)
		elif self.trial_period_start and self.is_trialling():
			_current_invoice_start = self.trial_period_start
		elif date:
			_current_invoice_start = date
		else:
			_current_invoice_start = nowdate()

		return _current_invoice_start

	def get_current_invoice_end(self, date: DateTimeLikeObject | None = None) -> DateTimeLikeObject:
		"""
		This returns the date of the end of the current billing period.
		If the subscription is in trial period, it will be set as the end of the
		trial period.
		If is not in a trial period, it will be `x` days from the beginning of the
		current billing period where `x` is the billing interval from the
		`Subscription Plan` in the `Subscription`.
		"""
		_current_invoice_end = None

		if self.is_trialling() and getdate(date) < getdate(self.trial_period_end):
			_current_invoice_end = self.trial_period_end
		else:
			billing_cycle_info = self.get_billing_cycle_data()
			if billing_cycle_info:
				if getdate(self.start_date) < getdate(date):
					_current_invoice_end = add_to_date(self.start_date, **billing_cycle_info)

					# For cases where trial period is for an entire billing interval
					if getdate(self.current_invoice_end) < getdate(date):
						_current_invoice_end = add_to_date(date, **billing_cycle_info)
				else:
					_current_invoice_end = add_to_date(date, **billing_cycle_info)
			else:
				_current_invoice_end = get_last_day(date)

			if self.follow_calendar_months:
				# Sets the end date
				# eg if date is 17-Feb-2022, the invoice will be generated per month ie
				# the invoice will be created from 17 Feb to 28 Feb
				billing_info = self.get_billing_cycle_and_interval()
				billing_interval_count = billing_info[0]["billing_interval_count"]
				_end = add_months(getdate(date), billing_interval_count - 1)
				_current_invoice_end = get_last_day(_end)

			if self.end_date and getdate(_current_invoice_end) > getdate(self.end_date):
				_current_invoice_end = self.end_date

		return _current_invoice_end

	@staticmethod
	def validate_plans_billing_cycle(billing_cycle_data: list[dict[str, str]]) -> None:
		"""
		Makes sure that all `Subscription Plan` in the `Subscription` have the
		same billing interval
		"""
		if billing_cycle_data and len(billing_cycle_data) != 1:
			frappe.throw(_("You can only have Plans with the same billing cycle in a Subscription"))

	def get_billing_cycle_and_interval(self) -> list[dict[str, str]]:
		"""
		Returns a dict representing the billing interval and cycle for this `Subscription`.
		You shouldn't need to call this directly. Use `get_billing_cycle` instead.
		"""
		plan_names = [plan.plan for plan in self.plans]

		subscription_plan = frappe.qb.DocType("Subscription Plan")
		billing_info = (
			frappe.qb.from_(subscription_plan)
			.select(subscription_plan.billing_interval, subscription_plan.billing_interval_count)
			.distinct()
			.where(subscription_plan.name.isin(plan_names))
		).run(as_dict=1)

		return billing_info

	def get_billing_cycle_data(self) -> dict[str, int]:
		"""
		Returns dict contain the billing cycle data.
		You shouldn't need to call this directly. Use `get_billing_cycle` instead.
		"""
		billing_info = self.get_billing_cycle_and_interval()
		if not billing_info:
			return None

		data = dict()
		interval = billing_info[0]["billing_interval"]
		interval_count = billing_info[0]["billing_interval_count"]

		if interval not in ["Day", "Week"]:
			data["days"] = -1

		if interval == "Day":
			data["days"] = interval_count - 1
		elif interval == "Week":
			data["days"] = interval_count * 7 - 1
		elif interval == "Month":
			data["months"] = interval_count
		elif interval == "Year":
			data["years"] = interval_count

		return data

	def set_subscription_status(self, posting_date: DateTimeLikeObject | None = None) -> None:
		"""
		Sets the status of the `Subscription`
		"""
		if self.is_trialling():
			self.status = "Trialling"
		elif self.status == "Active" and self.end_date and getdate(posting_date) > getdate(self.end_date):
			self.status = "Completed"
		elif self.is_past_grace_period():
			self.status = self.get_status_for_past_grace_period()
			self.cancelation_date = getdate(posting_date) if self.status == "Cancelled" else None
		elif self.current_invoice_is_past_due() and not self.is_past_grace_period():
			self.status = "Past Due Date"
		elif not self.has_outstanding_invoice():
			self.status = "Active"

	def is_trialling(self) -> bool:
		"""
		Returns `True` if the `Subscription` is in trial period.
		"""
		return not self.period_has_passed(self.trial_period_end)

	@staticmethod
	def period_has_passed(
		end_date: DateTimeLikeObject, posting_date: DateTimeLikeObject | None = None
	) -> bool:
		"""
		Returns true if the given `end_date` has passed
		"""
		# todo: test for illegal time
		if not end_date:
			return True

		return getdate(posting_date) > getdate(end_date)

	def get_status_for_past_grace_period(self) -> str:
		cancel_after_grace = cint(frappe.get_value("Subscription Settings", None, "cancel_after_grace"))
		status = "Unpaid"

		if cancel_after_grace:
			status = "Cancelled"

		return status

	def is_past_grace_period(self, posting_date: DateTimeLikeObject | None = None) -> bool:
		"""
		Returns `True` if the grace period for the `Subscription` has passed
		"""
		if not self.current_invoice_is_past_due():
			return

		grace_period = cint(frappe.get_value("Subscription Settings", None, "grace_period"))
		return getdate(posting_date) >= getdate(add_days(self.current_invoice.due_date, grace_period))

	def current_invoice_is_past_due(self, posting_date: DateTimeLikeObject | None = None) -> bool:
		"""
		Returns `True` if the current generated invoice is overdue
		"""
		if not self.current_invoice or self.is_paid(self.current_invoice):
			return False

		return getdate(posting_date) >= getdate(self.current_invoice.due_date)

	@property
	def invoice_document_type(self) -> str:
		return "Sales Invoice" if self.party_type == "Customer" else "Purchase Invoice"

	def validate(self) -> None:
		self.validate_trial_period()
		self.validate_plans_billing_cycle(self.get_billing_cycle_and_interval())
		self.validate_end_date()
		self.validate_to_follow_calendar_months()
		if not self.cost_center:
			self.cost_center = get_default_cost_center(self.get("company"))

		if self.is_new():
			self.set_subscription_status()

		self.validate_party_billing_currency()

	def validate_party_billing_currency(self):
		"""
		Subscription should be of the same currency as the Party's default billing currency or company default.
		"""
		if self.party:
			party_billing_currency = frappe.get_cached_value(
				self.party_type, self.party, "default_currency"
			) or frappe.get_cached_value("Company", self.company, "default_currency")

			plans = [x.plan for x in self.plans]
			subscription_plan_currencies = frappe.db.get_all(
				"Subscription Plan", filters={"name": ("in", plans)}, fields=["name", "currency"]
			)
			unsupported_plans = []
			for x in subscription_plan_currencies:
				if x.currency != party_billing_currency:
					unsupported_plans.append("{}".format(get_link_to_form("Subscription Plan", x.name)))

			if unsupported_plans:
				unsupported_plans = [
					_(
						"Below Subscription Plans are of different currency to the party default billing currency/Company currency: {0}"
					).format(frappe.bold(party_billing_currency)),
					*unsupported_plans,
				]

				frappe.throw(
					unsupported_plans, frappe.ValidationError, "Unsupported Subscription Plans", as_list=True
				)

	def validate_trial_period(self) -> None:
		"""
		Runs sanity checks on trial period dates for the `Subscription`
		"""
		if self.trial_period_start and self.trial_period_end:
			if getdate(self.trial_period_end) < getdate(self.trial_period_start):
				frappe.throw(_("Trial Period End Date Cannot be before Trial Period Start Date"))

		if self.trial_period_start and not self.trial_period_end:
			frappe.throw(_("Both Trial Period Start Date and Trial Period End Date must be set"))

		if self.trial_period_start and getdate(self.trial_period_start) > getdate(self.start_date):
			frappe.throw(_("Trial Period Start date cannot be after Subscription Start Date"))

	def validate_end_date(self) -> None:
		billing_cycle_info = self.get_billing_cycle_data()
		end_date = add_to_date(self.start_date, **billing_cycle_info)

		if self.end_date and getdate(self.end_date) <= getdate(end_date):
			frappe.throw(
				_("Subscription End Date must be after {0} as per the subscription plan").format(end_date)
			)

	def validate_to_follow_calendar_months(self) -> None:
		if not self.follow_calendar_months:
			return

		billing_info = self.get_billing_cycle_and_interval()

		if not self.end_date:
			frappe.throw(_("Subscription End Date is mandatory to follow calendar months"))

		if billing_info[0]["billing_interval"] != "Month":
			frappe.throw(_("Billing Interval in Subscription Plan must be Month to follow calendar months"))

	def generate_invoice(
		self,
		from_date: DateTimeLikeObject | None = None,
		to_date: DateTimeLikeObject | None = None,
		posting_date: DateTimeLikeObject | None = None,
	) -> Document:
		"""
		Creates a `Invoice` for the `Subscription`, updates `self.invoices` and
		saves the `Subscription`.
		Backwards compatibility
		"""
		return self.create_invoice(from_date=from_date, to_date=to_date, posting_date=posting_date)

	def create_invoice(
		self,
		from_date: DateTimeLikeObject | None = None,
		to_date: DateTimeLikeObject | None = None,
		posting_date: DateTimeLikeObject | None = None,
	) -> Document:
		"""
		Creates a `Invoice`, submits it and returns it
		"""
		# For backward compatibility
		# Earlier subscription didn't had any company field
		company = self.get("company") or get_default_company()
		if not company:
			frappe.throw(
				_(
					"Company is mandatory for generating an invoice. Please set a default company in Global Defaults."
				)
			)

		invoice = frappe.new_doc(self.invoice_document_type)
		invoice.company = company
		invoice.set_posting_time = 1

		if self.generate_invoice_at == "Beginning of the current subscription period":
			invoice.posting_date = self.current_invoice_start
		elif self.generate_invoice_at == "Days before the current subscription period":
			invoice.posting_date = posting_date or self.current_invoice_start
		else:
			invoice.posting_date = self.current_invoice_end

		invoice.cost_center = self.cost_center

		if self.invoice_document_type == "Sales Invoice":
			invoice.customer = self.party
		else:
			invoice.supplier = self.party
			if frappe.db.get_value("Supplier", self.party, "tax_withholding_category"):
				invoice.apply_tds = 1

		# Add party currency to invoice
		invoice.currency = get_party_account_currency(self.party_type, self.party, self.company)

		# Add dimensions in invoice for subscription:
		accounting_dimensions = get_accounting_dimensions()

		for dimension in accounting_dimensions:
			if self.get(dimension):
				invoice.update({dimension: self.get(dimension)})

		# Subscription is better suited for service items. I won't update `update_stock`
		# for that reason
		items_list = self.get_items_from_plans(self.plans, is_prorate())

		for item in items_list:
			item["cost_center"] = self.cost_center
			invoice.append("items", item)

		# Taxes
		tax_template = ""

		if self.invoice_document_type == "Sales Invoice" and self.sales_tax_template:
			tax_template = self.sales_tax_template
		if self.invoice_document_type == "Purchase Invoice" and self.purchase_tax_template:
			tax_template = self.purchase_tax_template

		if tax_template:
			invoice.taxes_and_charges = tax_template
			invoice.set_taxes()

		# Due date
		if self.days_until_due:
			invoice.append(
				"payment_schedule",
				{
					"due_date": add_days(invoice.posting_date, cint(self.days_until_due)),
					"invoice_portion": 100,
				},
			)

		# Discounts
		if self.is_trialling():
			invoice.additional_discount_percentage = 100
		else:
			if self.additional_discount_percentage:
				invoice.additional_discount_percentage = self.additional_discount_percentage

			if self.additional_discount_amount:
				invoice.discount_amount = self.additional_discount_amount

			if self.additional_discount_percentage or self.additional_discount_amount:
				discount_on = self.apply_additional_discount
				invoice.apply_discount_on = discount_on if discount_on else "Grand Total"

		# Subscription period
		invoice.subscription = self.name
		invoice.from_date = from_date or self.current_invoice_start
		invoice.to_date = to_date or self.current_invoice_end

		invoice.flags.ignore_mandatory = True

		invoice.set_missing_values()
		invoice.save()

		if self.submit_invoice:
			invoice.submit()

		return invoice

	def get_items_from_plans(self, plans: list[dict[str, str]], prorate: bool | None = None) -> list[dict]:
		"""
		Returns the `Item`s linked to `Subscription Plan`
		"""
		if prorate is None:
			prorate = False

		if prorate:
			prorate_factor = get_prorata_factor(
				self.current_invoice_end,
				self.current_invoice_start,
				cint(self.generate_invoice_at == "Beginning of the current subscription period"),
			)

		items = []
		party = self.party
		for plan in plans:
			plan_doc = frappe.get_doc("Subscription Plan", plan.plan)

			item_code = plan_doc.item

			if self.party == "Customer":
				deferred_field = "enable_deferred_revenue"
			else:
				deferred_field = "enable_deferred_expense"

			deferred = frappe.db.get_value("Item", item_code, deferred_field)

			if not prorate:
				item = {
					"item_code": item_code,
					"qty": plan.qty,
					"rate": get_plan_rate(
						plan.plan,
						plan.qty,
						party,
						self.current_invoice_start,
						self.current_invoice_end,
					),
					"cost_center": plan_doc.cost_center,
				}
			else:
				item = {
					"item_code": item_code,
					"qty": plan.qty,
					"rate": get_plan_rate(
						plan.plan,
						plan.qty,
						party,
						self.current_invoice_start,
						self.current_invoice_end,
						prorate_factor,
					),
					"cost_center": plan_doc.cost_center,
				}

			if deferred:
				item.update(
					{
						deferred_field: deferred,
						"service_start_date": self.current_invoice_start,
						"service_end_date": self.current_invoice_end,
					}
				)

			accounting_dimensions = get_accounting_dimensions()

			for dimension in accounting_dimensions:
				if plan_doc.get(dimension):
					item.update({dimension: plan_doc.get(dimension)})

			items.append(item)

		return items

	@frappe.whitelist()
	def process(self, posting_date: DateTimeLikeObject | None = None) -> bool:
		"""
		To be called by task periodically. It checks the subscription and takes appropriate action
		as need be. It calls either of these methods depending the `Subscription` status:
		1. `process_for_active`
		2. `process_for_past_due`
		"""
		if not self.is_current_invoice_generated(
			self.current_invoice_start, self.current_invoice_end
		) and self.can_generate_new_invoice(posting_date):
			self.generate_invoice(posting_date=posting_date)
			self.update_subscription_period(add_days(self.current_invoice_end, 1))
		elif posting_date and getdate(posting_date) > getdate(self.current_invoice_end):
			self.update_subscription_period()

		if self.cancel_at_period_end and (
			getdate(posting_date) >= getdate(self.current_invoice_end)
			or getdate(posting_date) >= getdate(self.end_date)
		):
			self.cancel_subscription()

		self.set_subscription_status(posting_date=posting_date)

		self.save()

	def can_generate_new_invoice(self, posting_date: DateTimeLikeObject | None = None) -> bool:
		if self.cancelation_date:
			return False

		if self.has_outstanding_invoice() and not self.generate_new_invoices_past_due_date:
			return False

		if self.generate_invoice_at == "Beginning of the current subscription period" and (
			getdate(posting_date) == getdate(self.current_invoice_start)
		):
			return True
		elif self.generate_invoice_at == "Days before the current subscription period" and (
			getdate(posting_date) == getdate(add_days(self.current_invoice_start, -1 * self.number_of_days))
		):
			return True
		elif getdate(posting_date) == getdate(self.current_invoice_end):
			return True
		else:
			return False

	def is_current_invoice_generated(
		self,
		_current_start_date: DateTimeLikeObject | None = None,
		_current_end_date: DateTimeLikeObject | None = None,
	) -> bool:
		if not (_current_start_date and _current_end_date):
			_current_start_date, _current_end_date = self._get_subscription_period(
				date=add_days(self.current_invoice_end, 1)
			)

		if self.current_invoice and getdate(_current_start_date) <= getdate(
			self.current_invoice.posting_date
		) <= getdate(_current_end_date):
			return True

		return False

	@property
	def current_invoice(self) -> Document | None:
		"""
		Adds property for accessing the current_invoice
		"""
		return self.get_current_invoice()

	def get_current_invoice(self) -> Document | None:
		"""
		Returns the most recent generated invoice.
		"""
		invoice = frappe.get_all(
			self.invoice_document_type,
			{
				"subscription": self.name,
			},
			limit=1,
			order_by="to_date desc",
			pluck="name",
		)

		if invoice:
			return frappe.get_doc(self.invoice_document_type, invoice[0])

	def cancel_subscription_at_period_end(self) -> None:
		"""
		Called when `Subscription.cancel_at_period_end` is truthy
		"""
		self.status = "Cancelled"
		self.cancelation_date = nowdate()

	@property
	def invoices(self) -> list[dict]:
		return frappe.get_all(
			self.invoice_document_type,
			filters={"subscription": self.name},
			order_by="from_date asc",
		)

	@staticmethod
	def is_paid(invoice: Document) -> bool:
		"""
		Return `True` if the given invoice is paid
		"""
		return invoice.status == "Paid"

	def has_outstanding_invoice(self) -> int:
		"""
		Returns `True` if the most recent invoice for the `Subscription` is not paid
		"""
		return frappe.db.count(
			self.invoice_document_type,
			{
				"subscription": self.name,
				"status": ["!=", "Paid"],
			},
		)

	@frappe.whitelist()
	def cancel_subscription(self) -> None:
		"""
		This sets the subscription as cancelled. It will stop invoices from being generated
		but it will not affect already created invoices.
		"""
		if self.status == "Cancelled":
			frappe.throw(_("subscription is already cancelled."), InvoiceCancelled)

		to_generate_invoice = (
			True
			if self.status == "Active"
			and not self.generate_invoice_at == "Beginning of the current subscription period"
			else False
		)
		self.status = "Cancelled"
		self.cancelation_date = nowdate()

		if to_generate_invoice:
			self.generate_invoice(self.current_invoice_start, self.cancelation_date)

		self.save()

	@frappe.whitelist()
	def restart_subscription(self, posting_date: DateTimeLikeObject | None = None) -> None:
		"""
		This sets the subscription as active. The subscription will be made to be like a new
		subscription and the `Subscription` will lose all the history of generated invoices
		it has.
		"""
		if not self.status == "Cancelled":
			frappe.throw(_("You cannot restart a Subscription that is not cancelled."), InvoiceNotCancelled)

		self.status = "Active"
		self.cancelation_date = None
		self.update_subscription_period(posting_date or nowdate())
		self.save()


def is_prorate() -> int:
	return cint(frappe.db.get_single_value("Subscription Settings", "prorate"))


def get_prorata_factor(
	period_end: DateTimeLikeObject,
	period_start: DateTimeLikeObject,
	is_prepaid: int | None = None,
) -> int | float:
	if is_prepaid:
		return 1

	diff = flt(date_diff(nowdate(), period_start) + 1)
	plan_days = flt(date_diff(period_end, period_start) + 1)
	return diff / plan_days


def process_all(subscription: str | None = None, posting_date: DateTimeLikeObject | None = None) -> None:
	"""
	Task to updates the status of all `Subscription` apart from those that are cancelled
	"""
	filters = {"status": ("!=", "Cancelled")}

	if subscription:
		filters["name"] = subscription

	for subscription in frappe.get_all("Subscription", filters, pluck="name"):
		try:
			subscription = frappe.get_doc("Subscription", subscription)
			subscription.process(posting_date)
			frappe.db.commit()
		except frappe.ValidationError:
			frappe.db.rollback()
			subscription.log_error("Subscription failed")
