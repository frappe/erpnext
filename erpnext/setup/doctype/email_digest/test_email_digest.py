# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, getdate, now_datetime, today

from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.selling.doctype.quotation.test_quotation import make_quotation
from erpnext.tests.utils import ERPNextTestSuite


class TestEmailDigest(ERPNextTestSuite):
	def test_dates_before_first_fiscal_year_have_zero_income_and_count(self):
		from erpnext.setup.doctype.email_digest.email_digest import (
			get_count_for_period,
			get_incomes_expenses_for_period,
		)

		date = getdate("1900-01-01")
		account = frappe.db.get_value("Account", {"company": "_Test Company", "is_group": 0}, "name")
		self.assertEqual(get_incomes_expenses_for_period(account, date, date), 0)
		self.assertEqual(get_count_for_period(account, "income", date, date), 0)
		digest = create_email_digest(company="_Test Company", do_not_save=True)
		digest.future_to_date = date
		self.assertEqual(digest.get_income_year_to_date()["value"], 0)

	def test_missing_future_fiscal_year_still_raises(self):
		from erpnext.accounts.utils import FiscalYearError
		from erpnext.setup.doctype.email_digest.email_digest import get_digest_fiscal_year

		with self.assertRaises(FiscalYearError):
			get_digest_fiscal_year(getdate("2200-01-01"))

	def test_scheduler_continues_after_a_digest_fails(self):
		from unittest.mock import patch

		from erpnext.setup.doctype.email_digest.email_digest import EmailDigest, send

		first = create_email_digest(name="Failing Email Digest", enabled=1)
		second = create_email_digest(name="Working Email Digest", enabled=1)
		delivered = []
		get_all = frappe.get_all

		def get_digests(doctype, *args, **kwargs):
			if doctype == "Email Digest":
				return [(first.name,), (second.name,)]
			return get_all(doctype, *args, **kwargs)

		def send_digest(digest):
			if digest.name == first.name:
				raise ValueError("digest failed")
			delivered.append(digest.name)

		with (
			patch("frappe.get_all", side_effect=get_digests),
			patch.object(EmailDigest, "send", send_digest),
			patch("frappe.log_error"),
		):
			send()
		self.assertEqual(delivered, [second.name])

	def test_project_list_links_to_projects(self):
		if not frappe.db.exists("Project Type", "External"):
			frappe.get_doc({"doctype": "Project Type", "project_type": "External"}).insert()
		frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": "Email Digest Link Test",
				"project_type": "External",
				"company": "_Test Company",
			}
		).insert()
		digest = create_email_digest(company="_Test Company", do_not_save=True)
		projects = digest.get_project_list()
		self.assertTrue(projects)
		for project in projects:
			self.assertIn("/desk/project/", project.link)

	def test_pending_card_links_use_correct_filters(self):
		from urllib.parse import unquote

		digest = create_email_digest(company="_Test Company", do_not_save=True)
		purchase_label = unquote(digest.get_purchase_orders_to_bill()["label"])
		quotation_label = unquote(digest.get_pending_quotations()["label"])
		self.assertIn("per_billed", purchase_label)
		self.assertNotIn("per_received", purchase_label)
		self.assertIn("docstatus=1", purchase_label)
		self.assertNotIn("per_received", quotation_label)
		self.assertIn("docstatus=1", quotation_label)
		self.assertIn("Expired", quotation_label)
		self.assertIn("docstatus=1", unquote(digest.get_purchase_order()["label"]))

	def test_purchase_order_totals_use_company_currency(self):
		digest = create_email_digest(company="_Test Company", do_not_save=True)
		digest.future_from_date = digest.future_to_date = today()
		before = digest.get_purchase_order()["value"]
		order = create_purchase_order(
			transaction_date=today(), currency="USD", conversion_factor=83, qty=1, rate=100, do_not_save=True
		)
		order.insert()
		order.submit()
		self.assertNotEqual(order.base_grand_total, order.grand_total)
		self.assertEqual(digest.get_purchase_order()["value"] - before, order.base_grand_total)

	def test_document_totals_exclude_drafts(self):
		digest = create_email_digest(company="_Test Company", do_not_save=True)
		before = digest.get_total_on("Purchase Order", today(), today())[0].count
		order = create_purchase_order(transaction_date=today(), do_not_save=True)
		order.insert()
		self.assertEqual(digest.get_total_on("Purchase Order", today(), today())[0].count, before)
		order.submit()
		self.assertEqual(digest.get_total_on("Purchase Order", today(), today())[0].count, before + 1)

	def test_pending_purchase_orders_exclude_drafts(self):
		digest = create_email_digest(company="_Test Company", do_not_save=True)
		digest.future_to_date = today()
		before = [
			digest.get_purchase_orders_to_bill()["count"],
			digest.get_purchase_orders_to_receive()["count"],
		]
		order = create_purchase_order(transaction_date=today(), do_not_save=True)
		order.insert()
		self.assertEqual(digest.get_purchase_orders_to_bill()["count"], before[0])
		self.assertEqual(digest.get_purchase_orders_to_receive()["count"], before[1])
		order.submit()
		self.assertEqual(digest.get_purchase_orders_to_bill()["count"], before[0] + 1)
		self.assertEqual(digest.get_purchase_orders_to_receive()["count"], before[1] + 1)

	def test_pending_quotations_exclude_drafts_and_expired(self):
		from erpnext.selling.doctype.quotation.quotation import set_expired_status

		set_expired_status()
		digest = create_email_digest(company="_Test Company", do_not_save=True)
		digest.future_to_date = today()
		before = digest.get_pending_quotations()["count"]
		quotation = make_quotation(transaction_date=add_days(today(), -2), do_not_save=True)
		quotation.valid_till = add_days(today(), -1)
		quotation.insert()
		self.assertEqual(digest.get_pending_quotations()["count"], before)
		quotation.submit()
		self.assertEqual(digest.get_pending_quotations()["count"], before + 1)
		set_expired_status()
		self.assertEqual(digest.get_pending_quotations()["count"], before)

	def test_expired_quotation_is_in_previous_period_if_still_valid_then(self):
		from erpnext.selling.doctype.quotation.quotation import set_expired_status

		set_expired_status()
		digest = create_email_digest(company="_Test Company", do_not_save=True)
		digest.future_to_date = today()
		digest.past_to_date = getdate(add_days(today(), -1))
		before = digest.get_pending_quotations()
		quotation = make_quotation(transaction_date=add_days(today(), -2), do_not_save=True)
		quotation.valid_till = add_days(today(), -1)
		quotation.insert()
		quotation.submit()
		set_expired_status()
		after = digest.get_pending_quotations()
		self.assertEqual(after["value"], before["value"])
		self.assertEqual(after["last_value"] - before["last_value"], quotation.base_grand_total)

	def test_purchase_orders_items_overdue_list_is_filtered_by_company(self):
		digest = create_email_digest(
			company="_Test Company",
			frequency="Daily",
			purchase_orders_items_overdue=1,
			name="Test Email Digest PO Company Filter",
		)
		backdate = add_days(today(), -1)

		po1 = create_purchase_order(transaction_date=backdate, do_not_save=True)
		po1.schedule_date = backdate
		po1.items[0].schedule_date = backdate
		po1.insert()
		po1.submit()

		po2 = create_purchase_order(
			company="_Test Company 1",
			warehouse="Stores - _TC1",
			transaction_date=backdate,
			do_not_save=True,
		)
		po2.schedule_date = backdate
		po2.items[0].schedule_date = backdate
		po2.insert()
		po2.submit()

		overdue_items = digest.get_purchase_orders_items_overdue_list()

		self.assertIn(po1.name, overdue_items)
		self.assertNotIn(po2.name, overdue_items)

	def test_get_todo_list_priority_and_date_ordering(self):
		"""Original SQL ordered by `field(priority,'High','Medium','Low') asc, date asc`: MySQL
		FIELD() returns 0 for empty/unknown priority (sorts FIRST under asc) and MariaDB sorts NULL
		dates FIRST. The conversion preserves this: the priority CASE uses else_(0) (unknown/empty
		priority sorts FIRST) and IfNull(date,'1000-01-01') keeps NULL dates FIRST, so the LIMIT-20
		slice is identical on both engines. The two assertions below exercise both branches and would
		fail if either sentinel were flipped to sort those rows last."""
		user = "_test_todo_order@example.com"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{"doctype": "User", "email": user, "first_name": "Todo Order", "send_welcome_email": 0}
			).insert(ignore_permissions=True)

		def mk(desc, priority, date):
			td = frappe.get_doc(
				{
					"doctype": "ToDo",
					"description": desc,
					"assigned_by": user,
					"status": "Open",
					"priority": "Medium",
				}
			).insert(ignore_permissions=True)
			frappe.db.set_value("ToDo", td.name, {"priority": priority, "date": date}, update_modified=False)
			return td.name

		empty_pri = mk("empty-priority", "", "2020-01-01")
		high_dated = mk("high-dated", "High", "2020-06-15")
		high_nulldate = mk("high-nulldate", "High", None)
		mk("low", "Low", "2020-03-01")

		rows = frappe.new_doc("Email Digest").get_todo_list(user_id=user)
		order = [r.name for r in rows]

		# unknown/empty priority (FIELD()=0) must sort before High
		self.assertLess(order.index(empty_pri), order.index(high_dated))
		# within the High tier, a NULL date must sort before a real date (MariaDB NULLs-first)
		self.assertLess(order.index(high_nulldate), order.index(high_dated))


def create_email_digest(**args):
	args = frappe._dict(args)
	doc = frappe.new_doc("Email Digest")
	doc.name = args.name or "Test Email Digest"
	doc.company = args.company or "_Test Company"
	doc.frequency = args.frequency or "Daily"
	doc.enabled = args.enabled or 0
	doc.bank_balance = args.bank_balance or 0
	doc.credit_balance = args.credit_balance or 0
	doc.invoiced_amount = args.invoiced_amount or 0
	doc.payables = args.payables or 0
	doc.sales_orders_to_bill = args.sales_orders_to_bill or 0
	doc.purchase_orders_to_bill = args.purchase_orders_to_bill or 0
	doc.sales_order = args.sales_order or 0
	doc.purchase_order = args.purchase_order or 0
	doc.sales_orders_to_deliver = args.sales_orders_to_deliver or 0
	doc.purchase_orders_to_receive = args.purchase_orders_to_receive or 0
	doc.sales_invoice = args.sales_invoice or 0
	doc.purchase_invoice = args.purchase_invoice or 0
	doc.new_quotations = args.new_quotations or 0
	doc.pending_quotations = args.pending_quotations or 0
	doc.issue = args.issue or 0
	doc.project = args.project or 0
	doc.purchase_orders_items_overdue = args.purchase_orders_items_overdue or 0
	doc.calendar_events = args.calendar_events or 0
	doc.todo_list = args.todo_list or 0
	doc.notifications = args.notifications or 0
	doc.add_quote = args.add_quote or 0

	for recipient in args.recipients or ["Administrator"]:
		doc.append("recipients", {"recipient": recipient})

	if not args.do_not_save:
		doc.insert()

	return doc


class TestEmailDigestDates(ERPNextTestSuite):
	"""The digest's reporting windows are pure date math driven by the frequency."""

	def make_digest(self, frequency, from_date="2026-06-15"):
		doc = frappe.new_doc("Email Digest")
		doc.frequency = frequency
		doc.from_date = getdate(from_date)
		doc.to_date = getdate(from_date)
		return doc

	def test_set_dates_daily_looks_back_one_day(self):
		doc = self.make_digest("Daily")
		doc.set_dates()
		self.assertEqual(doc.past_from_date, getdate("2026-06-14"))
		self.assertEqual(doc.past_to_date, getdate("2026-06-14"))

	def test_set_dates_weekly_looks_back_one_week(self):
		doc = self.make_digest("Weekly")
		doc.set_dates()
		self.assertEqual(doc.past_from_date, getdate("2026-06-08"))
		self.assertEqual(doc.past_to_date, getdate("2026-06-14"))

	def test_set_dates_monthly_looks_back_one_month(self):
		doc = self.make_digest("Monthly")
		doc.set_dates()
		self.assertEqual(doc.past_from_date, getdate("2026-05-15"))
		self.assertEqual(doc.past_to_date, getdate("2026-06-14"))

	def test_weekly_window_is_the_previous_monday_to_sunday(self):
		from_date, to_date = self.make_digest("Weekly").get_from_to_date()
		self.assertEqual(from_date.weekday(), 0)  # Monday
		self.assertEqual((to_date - from_date).days, 6)  # through Sunday
		self.assertLess(to_date, now_datetime().date())  # entirely in the past
