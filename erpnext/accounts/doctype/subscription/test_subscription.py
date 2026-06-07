# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt


import frappe
from frappe.utils.data import (
	add_days,
	add_months,
	add_to_date,
	add_years,
	cint,
	date_diff,
	flt,
	get_date_str,
	getdate,
	nowdate,
)

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.accounts.doctype.subscription.subscription import Subscription, get_prorata_factor, process_all
from erpnext.accounts.utils import update_subscription_on_invoice_update
from erpnext.tests.utils import ERPNextTestSuite


class TestSubscription(ERPNextTestSuite):
	def setUp(self):
		make_plans()
		create_parties()
		reset_settings()
		frappe.db.set_value("Company", "_Test Company", "accounts_frozen_till_date", None)

	def test_create_subscription_with_trial_with_correct_period(self):
		subscription = create_subscription(
			trial_period_start=nowdate(), trial_period_end=add_months(nowdate(), 1)
		)
		self.assertEqual(subscription.trial_period_start, nowdate())
		self.assertEqual(subscription.trial_period_end, add_months(nowdate(), 1))
		self.assertEqual(
			add_days(subscription.trial_period_end, 1), get_date_str(subscription.current_invoice_start)
		)
		self.assertEqual(
			add_to_date(subscription.current_invoice_start, months=1, days=-1),
			get_date_str(subscription.current_invoice_end),
		)
		self.assertEqual(subscription.invoices, [])
		self.assertEqual(subscription.status, "Trialing")

	def test_create_subscription_without_trial_with_correct_period(self):
		subscription = create_subscription()
		self.assertEqual(subscription.trial_period_start, None)
		self.assertEqual(subscription.trial_period_end, None)
		self.assertEqual(subscription.current_invoice_start, nowdate())
		self.assertEqual(subscription.current_invoice_end, add_to_date(nowdate(), months=1, days=-1))
		# No invoice is created
		self.assertEqual(len(subscription.invoices), 0)
		self.assertEqual(subscription.status, "Active")

	def test_create_subscription_trial_with_wrong_dates(self):
		subscription = create_subscription(
			trial_period_start=add_days(nowdate(), 30), trial_period_end=nowdate(), do_not_save=True
		)
		self.assertRaises(frappe.ValidationError, subscription.save)

	def test_invoice_is_generated_at_end_of_billing_period(self):
		# Back-dated postpaid period has already ended, so catch-up bills it on creation
		# and advances to the next period.
		subscription = create_subscription(start_date="2018-01-01")
		self.assertEqual(len(subscription.invoices), 1)
		self.assertEqual(subscription.status, "Unpaid")
		self.assertEqual(getdate(subscription.current_invoice_start), getdate("2018-02-01"))
		self.assertEqual(getdate(subscription.current_invoice_end), getdate("2018-02-28"))

	def test_status_goes_back_to_active_after_invoice_is_paid(self):
		subscription = create_subscription(
			start_date="2018-01-01", generate_invoice_at="Beginning of the current subscription period"
		)
		subscription.process(posting_date="2018-01-01")  # generate first invoice
		self.assertEqual(len(subscription.invoices), 1)

		# Status is unpaid as Days until Due is zero and grace period is Zero
		self.assertEqual(subscription.status, "Unpaid")

		subscription.get_current_invoice()
		current_invoice = subscription.get_current_invoice()

		self.assertIsNotNone(current_invoice)

		current_invoice.db_set("outstanding_amount", 0)
		current_invoice.db_set("status", "Paid")
		subscription.process()

		self.assertEqual(subscription.status, "Active")
		self.assertEqual(subscription.current_invoice_start, add_months(subscription.start_date, 1))
		self.assertEqual(len(subscription.invoices), 1)

	def test_subscription_cancel_after_grace_period(self):
		settings = frappe.get_single("Subscription Settings")
		settings.cancel_after_grace = 1
		settings.save()

		# Back-dated unpaid invoice is already past its (zero) grace period, so catch-up
		# cancels the subscription on creation.
		subscription = create_subscription(start_date="2018-01-01")
		self.assertEqual(len(subscription.invoices), 1)
		self.assertEqual(subscription.status, "Cancelled")

	def test_subscription_unpaid_after_grace_period(self):
		settings = frappe.get_single("Subscription Settings")
		default_grace_period_action = settings.cancel_after_grace
		settings.cancel_after_grace = 0
		settings.save()

		subscription = create_subscription(start_date="2018-01-01")
		subscription.process(posting_date="2018-01-31")  # generate first invoice

		# Status is unpaid as Days until Due is zero and grace period is Zero
		self.assertEqual(subscription.status, "Unpaid")

		settings.cancel_after_grace = default_grace_period_action
		settings.save()

	def test_subscription_invoice_days_until_due(self):
		_date = add_months(nowdate(), -1)
		subscription = create_subscription(start_date=_date, days_until_due=10)

		subscription.process(posting_date=subscription.current_invoice_end)  # generate first invoice
		self.assertEqual(len(subscription.invoices), 1)
		self.assertEqual(subscription.status, "Active")

	def test_subscription_is_past_due_doesnt_change_within_grace_period(self):
		settings = frappe.get_single("Subscription Settings")
		grace_period = settings.grace_period
		settings.grace_period = 1000
		settings.save()

		subscription = create_subscription(start_date=add_days(nowdate(), -1000))

		subscription.process(posting_date=subscription.current_invoice_end)  # generate first invoice
		self.assertEqual(subscription.status, "Grace Period")

		subscription.process()
		# Grace period is 1000 days so status should remain as Grace Period
		self.assertEqual(subscription.status, "Grace Period")

		subscription.process()
		self.assertEqual(subscription.status, "Grace Period")

		subscription.process()
		self.assertEqual(subscription.status, "Grace Period")

		settings.grace_period = grace_period
		settings.save()

	def test_subscription_remains_active_during_invoice_period(self):
		subscription = create_subscription()  # no changes expected

		self.assertEqual(subscription.status, "Active")
		self.assertEqual(subscription.current_invoice_start, nowdate())
		self.assertEqual(subscription.current_invoice_end, add_to_date(nowdate(), months=1, days=-1))
		self.assertEqual(len(subscription.invoices), 0)

		subscription.process()  # no changes expected still
		self.assertEqual(subscription.status, "Active")
		self.assertEqual(subscription.current_invoice_start, nowdate())
		self.assertEqual(subscription.current_invoice_end, add_to_date(nowdate(), months=1, days=-1))
		self.assertEqual(len(subscription.invoices), 0)

		subscription.process()  # no changes expected yet still
		self.assertEqual(subscription.status, "Active")
		self.assertEqual(subscription.current_invoice_start, nowdate())
		self.assertEqual(subscription.current_invoice_end, add_to_date(nowdate(), months=1, days=-1))
		self.assertEqual(len(subscription.invoices), 0)

	def test_subscription_cancellation(self):
		subscription = create_subscription()
		subscription.cancel_subscription()

		self.assertEqual(subscription.status, "Cancelled")

	def test_subscription_cancellation_invoices(self):
		settings = frappe.get_single("Subscription Settings")
		to_prorate = settings.prorate
		settings.prorate = 1
		settings.save()

		subscription = create_subscription()

		self.assertEqual(subscription.status, "Active")

		subscription.cancel_subscription()
		# Invoice must have been generated
		self.assertEqual(len(subscription.invoices), 1)

		invoice = subscription.get_current_invoice()
		diff = flt(date_diff(nowdate(), subscription.current_invoice_start) + 1)
		plan_days = flt(date_diff(subscription.current_invoice_end, subscription.current_invoice_start) + 1)
		prorate_factor = flt(diff / plan_days)

		self.assertEqual(
			flt(
				get_prorata_factor(
					subscription.current_invoice_end,
					subscription.current_invoice_start,
					cint(subscription.generate_invoice_at == "Beginning of the current subscription period"),
				),
				2,
			),
			flt(prorate_factor, 2),
		)
		self.assertEqual(flt(invoice.grand_total, 2), flt(prorate_factor * 900, 2))
		self.assertEqual(subscription.status, "Cancelled")

		settings.prorate = to_prorate
		settings.save()

	def test_subscription_cancellation_invoices_with_prorata_false(self):
		settings = frappe.get_single("Subscription Settings")
		to_prorate = settings.prorate
		settings.prorate = 0
		settings.save()

		subscription = create_subscription()
		subscription.cancel_subscription()
		invoice = subscription.get_current_invoice()

		self.assertEqual(invoice.grand_total, 900)

		settings.prorate = to_prorate
		settings.save()

	def test_subscription_cancellation_invoices_with_prorata_true(self):
		settings = frappe.get_single("Subscription Settings")
		to_prorate = settings.prorate
		settings.prorate = 1
		settings.save()

		subscription = create_subscription()
		subscription.cancel_subscription()

		invoice = subscription.get_current_invoice()
		diff = flt(date_diff(nowdate(), subscription.current_invoice_start) + 1)
		plan_days = flt(date_diff(subscription.current_invoice_end, subscription.current_invoice_start) + 1)
		prorate_factor = flt(diff / plan_days)

		self.assertEqual(flt(invoice.grand_total, 2), flt(prorate_factor * 900, 2))

		settings.prorate = to_prorate
		settings.save()

	def test_subscription_cancellation_and_process(self):
		settings = frappe.get_single("Subscription Settings")
		default_grace_period_action = settings.cancel_after_grace
		settings.cancel_after_grace = 1
		settings.save()

		# Back-dated unpaid invoice past grace -> cancelled with one invoice on creation.
		subscription = create_subscription(start_date="2018-01-01")
		self.assertEqual(subscription.status, "Cancelled")
		self.assertEqual(len(subscription.invoices), 1)

		# Re-processing a cancelled subscription is a no-op.
		subscription.process()
		self.assertEqual(subscription.status, "Cancelled")
		self.assertEqual(len(subscription.invoices), 1)

		settings.cancel_after_grace = default_grace_period_action
		settings.save()

	def test_subscription_restart_and_process(self):
		settings = frappe.get_single("Subscription Settings")
		default_grace_period_action = settings.cancel_after_grace
		settings.grace_period = 0
		settings.cancel_after_grace = 0
		settings.save()

		subscription = create_subscription(start_date="2018-01-01")
		subscription.process(posting_date="2018-01-31")  # generate first invoice

		# Status is unpaid as Days until Due is zero and grace period is Zero
		self.assertEqual(subscription.status, "Unpaid")

		subscription.cancel_subscription()
		self.assertEqual(subscription.status, "Cancelled")

		subscription.restart_subscription()
		self.assertEqual(subscription.status, "Active")
		self.assertEqual(len(subscription.invoices), 1)

		subscription.process()
		self.assertEqual(subscription.status, "Unpaid")
		self.assertEqual(len(subscription.invoices), 1)

		subscription.process()
		self.assertEqual(subscription.status, "Unpaid")
		self.assertEqual(len(subscription.invoices), 1)

		settings.cancel_after_grace = default_grace_period_action
		settings.save()

	def test_subscription_unpaid_back_to_active(self):
		settings = frappe.get_single("Subscription Settings")
		default_grace_period_action = settings.cancel_after_grace
		settings.cancel_after_grace = 0
		settings.save()

		subscription = create_subscription(
			start_date="2018-01-01", generate_invoice_at="Beginning of the current subscription period"
		)
		subscription.process(subscription.current_invoice_start)  # generate first invoice
		# This should change status to Unpaid since grace period is 0
		self.assertEqual(subscription.status, "Unpaid")

		invoice = subscription.get_current_invoice()
		invoice.db_set("outstanding_amount", 0)
		invoice.db_set("status", "Paid")

		subscription.process()
		self.assertEqual(subscription.status, "Active")

		# A new invoice is generated
		subscription.process(posting_date=subscription.current_invoice_start)
		self.assertEqual(subscription.status, "Unpaid")

		settings.cancel_after_grace = default_grace_period_action
		settings.save()

	def test_restart_active_subscription(self):
		subscription = create_subscription()
		self.assertRaises(frappe.ValidationError, subscription.restart_subscription)

	def test_subscription_invoice_discount_percentage(self):
		subscription = create_subscription(additional_discount_percentage=10)
		subscription.cancel_subscription()

		invoice = subscription.get_current_invoice()

		self.assertEqual(invoice.additional_discount_percentage, 10)
		self.assertEqual(invoice.apply_discount_on, "Grand Total")

	def test_subscription_invoice_discount_amount(self):
		subscription = create_subscription(additional_discount_amount=11)
		subscription.cancel_subscription()

		invoice = subscription.get_current_invoice()

		self.assertEqual(invoice.discount_amount, 11)
		self.assertEqual(invoice.apply_discount_on, "Grand Total")

	def test_prepaid_subscriptions(self):
		# Create a non pre-billed subscription, processing should not create
		# invoices.
		subscription = create_subscription()
		subscription.process()
		self.assertEqual(len(subscription.invoices), 0)

		# Change the subscription type to prebilled and process it.
		# Prepaid invoice should be generated
		subscription.generate_invoice_at = "Beginning of the current subscription period"
		subscription.save()
		subscription.process()

		self.assertEqual(len(subscription.invoices), 1)

	def test_prepaid_subscriptions_with_prorate_true(self):
		settings = frappe.get_single("Subscription Settings")
		to_prorate = settings.prorate
		settings.prorate = 1
		settings.save()

		subscription = create_subscription(generate_invoice_at="Beginning of the current subscription period")
		subscription.process()
		subscription.cancel_subscription()

		self.assertEqual(len(subscription.invoices), 1)

		current_inv = subscription.get_current_invoice()
		self.assertEqual(current_inv.status, "Unpaid")

		prorate_factor = 1

		self.assertEqual(flt(current_inv.grand_total, 2), flt(prorate_factor * 900, 2))

		settings.prorate = to_prorate
		settings.save()

	def test_subscription_with_follow_calendar_months(self):
		subscription = frappe.new_doc("Subscription")
		subscription.company = "_Test Company"
		subscription.party_type = "Supplier"
		subscription.party = "_Test Supplier"
		subscription.generate_invoice_at = "Beginning of the current subscription period"
		subscription.follow_calendar_months = 1

		# select subscription start date as "2018-01-15"
		subscription.start_date = "2018-01-15"
		subscription.end_date = "2018-07-15"
		subscription.append("plans", {"plan": "_Test Plan Name 4", "qty": 1})
		subscription.save()

		# The first (prepaid) period is billed on creation. Even though the subscription
		# starts at "2018-01-15" with a 3-month interval, follow_calendar_months ends the
		# first invoice at "2018-03-31" instead of "2018-04-14".
		self.assertEqual(len(subscription.invoices), 1)
		self.assertEqual(
			getdate(frappe.db.get_value("Purchase Invoice", subscription.invoices[0].name, "to_date")),
			getdate("2018-03-31"),
		)

	def test_subscription_generate_invoice_past_due(self):
		# With `generate_new_invoices_past_due_date` enabled, catch-up bills every elapsed
		# 3-month period up to the end date on creation, even while previous ones are unpaid.
		subscription = create_subscription(
			start_date="2018-01-01",
			end_date="2018-12-31",
			party_type="Supplier",
			party="_Test Supplier",
			generate_invoice_at="Beginning of the current subscription period",
			generate_new_invoices_past_due_date=1,
			plans=[{"plan": "_Test Plan Name 4", "qty": 1}],
		)

		self.assertEqual(len(subscription.invoices), 4)
		self.assertEqual(subscription.status, "Unpaid")

	def test_subscription_without_generate_invoice_past_due(self):
		subscription = create_subscription(
			start_date="2018-01-01",
			generate_invoice_at="Beginning of the current subscription period",
			plans=[{"plan": "_Test Plan Name 4", "qty": 1}],
		)

		# Process subscription and create first invoice
		# Subscription status will be unpaid since due date has already passed
		subscription.process(posting_date="2018-01-01")
		self.assertEqual(len(subscription.invoices), 1)
		self.assertEqual(subscription.status, "Unpaid")

		subscription.process(posting_date="2018-04-01")
		self.assertEqual(len(subscription.invoices), 1)

	def test_multi_currency_subscription(self):
		party = "_Test Subscription Customer"
		frappe.db.set_value("Customer", party, "default_currency", "USD")
		subscription = create_subscription(
			start_date="2018-01-01",
			generate_invoice_at="Beginning of the current subscription period",
			plans=[{"plan": "_Test Plan Multicurrency", "qty": 1, "currency": "USD"}],
			party=party,
		)

		subscription.process(posting_date="2018-01-01")
		self.assertEqual(len(subscription.invoices), 1)
		self.assertEqual(subscription.status, "Unpaid")

		# Check the currency of the created invoice
		currency = frappe.db.get_value("Sales Invoice", subscription.invoices[0].name, "currency")
		self.assertEqual(currency, "USD")

	@ERPNextTestSuite.change_settings(
		"Accounts Settings",
		{"allow_multi_currency_invoices_against_single_party_account": 1},
	)
	def test_multi_currency_subscription_with_default_company_currency(self):
		party = "Test Subscription Customer Multi Currency"
		frappe.db.set_value("Customer", party, "default_currency", "USD")
		subscription = create_subscription(
			start_date="2018-01-01",
			generate_invoice_at="Beginning of the current subscription period",
			plans=[{"plan": "_Test Plan Multicurrency", "qty": 1, "currency": "USD"}],
			party=party,
		)

		subscription.process(posting_date="2018-01-01")
		self.assertEqual(len(subscription.invoices), 1)
		self.assertEqual(subscription.status, "Unpaid")

		# Check the currency of the created invoice
		currency = frappe.db.get_value("Sales Invoice", subscription.invoices[0].name, "currency")
		self.assertEqual(currency, "USD")

	def test_subscription_recovery(self):
		"""Test if Subscription recovers when start/end date run out of sync with created invoices."""
		subscription = create_subscription(
			start_date="2021-01-01",
			end_date="2021-02-28",
			submit_invoice=0,
			generate_new_invoices_past_due_date=1,
			party="_Test Subscription Customer John Doe",
		)

		# Catch-up bills both elapsed months on creation.
		self.assertEqual(len(subscription.invoices), 2)
		self.assertEqual(
			getdate(frappe.db.get_value("Sales Invoice", subscription.invoices[0].name, "from_date")),
			getdate("2021-01-01"),
		)
		self.assertEqual(
			getdate(frappe.db.get_value("Sales Invoice", subscription.invoices[1].name, "from_date")),
			getdate("2021-02-01"),
		)

		# Re-processing much later must not duplicate the already-billed periods.
		subscription.process(posting_date="2022-01-31")

		self.assertEqual(len(subscription.invoices), 2)
		self.assertEqual(
			getdate(frappe.db.get_value("Sales Invoice", subscription.invoices[0].name, "from_date")),
			getdate("2021-01-01"),
		)
		self.assertEqual(
			getdate(frappe.db.get_value("Sales Invoice", subscription.invoices[1].name, "from_date")),
			getdate("2021-02-01"),
		)

	def test_subscription_invoice_generation_before_days(self):
		# "Days before" trigger fires 10 days ahead of each period; catch-up bills both
		# elapsed periods (within the end date) on creation.
		subscription = create_subscription(
			start_date="2023-01-01",
			end_date="2023-02-28",
			generate_invoice_at="Days before the current subscription period",
			number_of_days=10,
			generate_new_invoices_past_due_date=1,
		)

		self.assertEqual(len(subscription.invoices), 2)

	def test_future_subscription(self):
		"""Force-Fetch should not process future subscriptions"""
		subscription = create_subscription(
			start_date=add_months(nowdate(), 1),
			submit_invoice=0,
			generate_new_invoices_past_due_date=1,
			party="_Test Subscription Customer John Doe",
		)
		subscription.force_fetch_subscription_updates()
		subscription.reload()
		self.assertEqual(len(subscription.invoices), 0)

	def test_invoice_generation_days_before_subscription_period_with_prorate(self):
		settings = frappe.get_single("Subscription Settings")
		settings.prorate = 1
		settings.save()

		create_plan(
			plan_name="_Test Plan Name 5",
			cost=1000,
			billing_interval="Year",
			billing_interval_count=1,
			currency="INR",
		)

		start_date = add_days(nowdate(), 2)

		subscription = create_subscription(
			start_date=start_date,
			party_type="Supplier",
			party="_Test Supplier",
			generate_invoice_at="Days before the current subscription period",
			generate_new_invoices_past_due_date=1,
			number_of_days=2,
			plans=[{"plan": "_Test Plan Name 5", "qty": 1}],
		)
		subscription.process(nowdate())
		self.assertEqual(len(subscription.invoices), 1)

	def test_subscription_auto_cancellation(self):
		create_plan(
			plan_name="_Test plan name 10",
			cost=80,
			currency="INR",
			billing_interval="Day",
			billing_interval_count=3,
		)
		start_date = getdate("2025-01-01")
		subscription = create_subscription(
			start_date=start_date,
			end_date=add_days(start_date, 8),
			cancel_at_period_end=1,
			generate_new_invoices_past_due_date=1,
			generate_invoice_at="Beginning of the current subscription period",
			plans=[{"plan": "_Test plan name 10", "qty": 1}],
		)
		# Catch-up billing on creation generates every elapsed period and cancels at end
		self.assertEqual(len(subscription.invoices), 3)
		self.assertEqual(subscription.status, "Cancelled")

	def test_subscription_auto_cancellation_uneven_cycle(self):
		create_plan(
			plan_name="_Test plan name 10",
			cost=80,
			currency="INR",
			billing_interval="Day",
			billing_interval_count=3,
		)
		start_date = getdate("2025-01-01")
		subscription = create_subscription(
			start_date=start_date,
			end_date=add_days(start_date, 6),
			cancel_at_period_end=1,
			generate_new_invoices_past_due_date=1,
			generate_invoice_at="Beginning of the current subscription period",
			plans=[{"plan": "_Test plan name 10", "qty": 1}],
		)

		# Catch-up billing on creation incl. the partial last cycle, then cancels at end
		self.assertEqual(len(subscription.invoices), 3)
		self.assertEqual(subscription.status, "Cancelled")

		self.assertRaises(frappe.ValidationError, subscription.process, posting_date=add_days(start_date, 7))

	def test_invoice_generated_when_scheduler_runs_one_day_late(self):
		# The trigger date (period end) is long past, yet catch-up still bills the period
		# on creation (Bug 1: the check is `>= trigger`, not `== trigger`).
		subscription = create_subscription(start_date="2018-01-01")
		self.assertEqual(len(subscription.invoices), 1)

	def test_deferred_revenue_applied_for_customer_subscription(self):
		item_code = "_Test Non Stock Item"
		frappe.db.set_value("Item", item_code, "enable_deferred_revenue", 1)
		try:
			# Build the period without saving, so on-create billing doesn't try to post an
			# invoice (the deferred item has no account configured). This only exercises the
			# item-mapping helper.
			subscription = create_subscription(start_date="2018-01-01", do_not_save=True)
			subscription.update_subscription_period("2018-01-01")
			items = subscription.get_items_from_plans(subscription.plans)
			self.assertEqual(items[0].get("enable_deferred_revenue"), 1)
			self.assertEqual(getdate(items[0]["service_start_date"]), getdate("2018-01-01"))
			self.assertEqual(getdate(items[0]["service_end_date"]), getdate("2018-01-31"))
		finally:
			frappe.db.set_value("Item", item_code, "enable_deferred_revenue", 0)

	def test_validate_end_date_with_no_plans_does_not_crash(self):
		sub = frappe.new_doc("Subscription")
		sub.party_type = "Customer"
		sub.party = "_Test Customer"
		sub.company = "_Test Company"
		sub.start_date = "2018-01-01"
		sub.end_date = "2018-03-01"
		try:
			sub.validate_end_date()
		except TypeError as e:
			self.fail(f"validate_end_date crashed with no plans: {e}")

	def test_process_all_logs_error_when_first_subscription_fails(self):
		sub1 = create_subscription(start_date="2018-01-01")
		sub2 = create_subscription(start_date="2018-01-02")

		processed = []
		original_process = Subscription.process
		original_rollback = frappe.db.rollback

		def patched(self, posting_date=None):
			processed.append(self.name)
			if self.name == sub1.name:
				raise frappe.ValidationError("forced failure")

		Subscription.process = patched
		# process_all calls frappe.db.rollback() on error which would otherwise wipe
		# the test transaction; stub it so we can observe the iteration in isolation.
		frappe.db.rollback = lambda *a, **kw: None
		try:
			process_all([sub1.name, sub2.name])
		finally:
			Subscription.process = original_process
			frappe.db.rollback = original_rollback

		self.assertEqual(processed, [sub1.name, sub2.name])

	def test_subscription_auto_completion(self):
		create_plan(
			plan_name="_Test Plan 3 Day",
			cost=100,
			billing_interval="Day",
			billing_interval_count=3,
			currency="INR",
		)

		start_date = getdate("2025-01-01")
		end_date = add_days(start_date, 6)

		subscription = create_subscription(
			start_date=start_date,
			end_date=end_date,
			party_type="Customer",
			party="_Test Customer",
			generate_invoice_at="Beginning of the current subscription period",
			generate_new_invoices_past_due_date=1,
			plans=[{"plan": "_Test Plan 3 Day", "qty": 1}],
		)

		for day in range(0, 10):
			if subscription.status == "Cancelled":
				break
			subscription.process(posting_date=add_days(start_date, day))

		invoices = frappe.get_all(
			"Sales Invoice",
			filters={"subscription": subscription.name, "docstatus": 1},
			fields=["name", "from_date", "to_date"],
			order_by="from_date asc",
		)
		for invoice in invoices:
			pi = get_payment_entry("Sales Invoice", invoice.name)
			pi.submit()
		# Paying the invoices refreshes the subscription via the Payment Entry hook, so
		# reload before processing the stale in-memory copy.
		subscription.reload()
		# After processing through all days, subscription should be completed
		subscription.process(posting_date=add_days(end_date, 1))
		self.assertEqual(subscription.status, "Completed")

	def test_status_updates_immediately_when_invoice_paid(self):
		subscription = create_subscription(
			start_date=nowdate(),
			generate_invoice_at="Beginning of the current subscription period",
			submit_invoice=1,
		)
		subscription.process(posting_date=nowdate())
		self.assertEqual(subscription.status, "Unpaid")

		invoice = subscription.get_current_invoice()
		payment = get_payment_entry("Sales Invoice", invoice.name)
		payment.submit()

		subscription.reload()
		self.assertEqual(subscription.status, "Active")

	def test_invoice_update_hook_refreshes_subscription_status(self):
		subscription = create_subscription(
			start_date=nowdate(),
			generate_invoice_at="Beginning of the current subscription period",
			submit_invoice=1,
		)
		subscription.process(posting_date=nowdate())
		self.assertEqual(subscription.status, "Unpaid")

		invoice = subscription.get_current_invoice()
		invoice.db_set("outstanding_amount", 0)
		invoice.db_set("status", "Paid")

		update_subscription_on_invoice_update(invoice)

		subscription.reload()
		self.assertEqual(subscription.status, "Active")

	def test_payment_entry_triggers_subscription_status_update(self):
		# Test that payment entry → invoice → subscription status update chain works
		subscription = create_subscription(
			start_date=nowdate(),
			generate_invoice_at="Beginning of the current subscription period",
			submit_invoice=1,
		)
		subscription.process(posting_date=nowdate())
		self.assertEqual(subscription.status, "Unpaid")

		invoice = subscription.get_current_invoice()
		self.assertIsNotNone(invoice)
		self.assertGreater(invoice.outstanding_amount, 0)

		# Create and submit payment entry
		payment_entry = get_payment_entry(invoice.doctype, invoice.name, bank_account="_Test Bank - _TC")
		payment_entry.reference_no = "12345"
		payment_entry.reference_date = nowdate()
		payment_entry.submit()

		# Subscription status should now be Active (via on_update_after_submit hook)
		subscription.reload()
		self.assertEqual(subscription.status, "Active")

	def test_first_invoice_generated_on_create_for_prepaid(self):
		subscription = create_subscription(
			start_date=nowdate(),
			generate_invoice_at="Beginning of the current subscription period",
		)
		self.assertEqual(len(subscription.invoices), 1)

	def test_first_invoice_not_generated_on_create_during_trial(self):
		subscription = create_subscription(
			start_date=nowdate(),
			trial_period_start=nowdate(),
			trial_period_end=add_days(nowdate(), 30),
			generate_invoice_at="Beginning of the current subscription period",
		)
		self.assertEqual(len(subscription.invoices), 0)
		self.assertEqual(subscription.status, "Trialing")

	def test_first_invoice_not_generated_during_bulk_import(self):
		frappe.flags.in_import = True
		try:
			subscription = create_subscription(
				start_date=nowdate(),
				generate_invoice_at="Beginning of the current subscription period",
			)
			self.assertEqual(len(subscription.invoices), 0)
		finally:
			frappe.flags.in_import = False

	def test_first_invoice_not_generated_for_future_dated_subscription(self):
		subscription = create_subscription(
			start_date=add_days(nowdate(), 10),
			generate_invoice_at="Beginning of the current subscription period",
		)
		self.assertEqual(len(subscription.invoices), 0)


def make_plans():
	create_plan(plan_name="_Test Plan Name", cost=900, currency="INR")
	create_plan(plan_name="_Test Plan Name 2", cost=1999, currency="INR")
	create_plan(
		plan_name="_Test Plan Name 3",
		cost=1999,
		billing_interval="Day",
		billing_interval_count=14,
		currency="INR",
	)
	create_plan(
		plan_name="_Test Plan Name 4",
		cost=20000,
		billing_interval="Month",
		billing_interval_count=3,
		currency="INR",
	)
	create_plan(plan_name="_Test Plan Multicurrency", cost=50, billing_interval="Month", currency="USD")


def create_plan(**kwargs):
	if not frappe.db.exists("Subscription Plan", kwargs.get("plan_name")):
		plan = frappe.new_doc("Subscription Plan")
		plan.plan_name = kwargs.get("plan_name") or "_Test Plan Name"
		plan.item = kwargs.get("item") or "_Test Non Stock Item"
		plan.price_determination = kwargs.get("price_determination") or "Fixed Rate"
		plan.cost = kwargs.get("cost") or 1000
		plan.billing_interval = kwargs.get("billing_interval") or "Month"
		plan.billing_interval_count = kwargs.get("billing_interval_count") or 1
		plan.currency = kwargs.get("currency")
		plan.insert()


def create_parties():
	if not frappe.db.exists("Supplier", "_Test Supplier"):
		supplier = frappe.new_doc("Supplier")
		supplier.supplier_name = "_Test Supplier"
		supplier.supplier_group = "All Supplier Groups"
		supplier.insert()

	if not frappe.db.exists("Customer", "_Test Subscription Customer"):
		customer = frappe.new_doc("Customer")
		customer.customer_name = "_Test Subscription Customer"
		customer.default_currency = "USD"
		customer.append("accounts", {"company": "_Test Company", "account": "_Test Receivable USD - _TC"})
		customer.insert()

	if not frappe.db.exists("Customer", "_Test Subscription Customer Multi Currency"):
		customer = frappe.new_doc("Customer")
		customer.customer_name = "Test Subscription Customer Multi Currency"
		customer.default_currency = "USD"
		customer.insert()

	if not frappe.db.exists("Customer", "_Test Subscription Customer John Doe"):
		customer = frappe.new_doc("Customer")
		customer.customer_name = "_Test Subscription Customer John Doe"
		customer.append("accounts", {"company": "_Test Company", "account": "_Test Receivable - _TC"})
		customer.insert()


def reset_settings():
	settings = frappe.get_single("Subscription Settings")
	settings.grace_period = 0
	settings.cancel_after_grace = 0
	settings.save()


def create_subscription(**kwargs):
	subscription = frappe.new_doc("Subscription")
	subscription.party_type = kwargs.get("party_type") or "Customer"
	subscription.company = kwargs.get("company") or "_Test Company"
	subscription.party = kwargs.get("party") or "_Test Customer"
	subscription.trial_period_start = kwargs.get("trial_period_start")
	subscription.trial_period_end = kwargs.get("trial_period_end")
	subscription.start_date = kwargs.get("start_date")
	subscription.end_date = kwargs.get("end_date")
	subscription.generate_invoice_at = kwargs.get("generate_invoice_at")
	subscription.additional_discount_percentage = kwargs.get("additional_discount_percentage")
	subscription.additional_discount_amount = kwargs.get("additional_discount_amount")
	subscription.follow_calendar_months = kwargs.get("follow_calendar_months")
	subscription.generate_new_invoices_past_due_date = kwargs.get("generate_new_invoices_past_due_date")
	subscription.submit_invoice = kwargs.get("submit_invoice")
	subscription.days_until_due = kwargs.get("days_until_due")
	subscription.number_of_days = kwargs.get("number_of_days")
	subscription.cancel_at_period_end = kwargs.get("cancel_at_period_end")

	if not kwargs.get("plans"):
		subscription.append("plans", {"plan": "_Test Plan Name", "qty": 1})
	else:
		for plan in kwargs.get("plans"):
			subscription.append("plans", plan)

	if kwargs.get("do_not_save"):
		return subscription

	subscription.save()

	return subscription
