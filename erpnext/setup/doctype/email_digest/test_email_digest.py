# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, getdate, now_datetime, today

from erpnext.buying.doctype.purchase_order.test_purchase_order import create_purchase_order
from erpnext.tests.utils import ERPNextTestSuite


class TestEmailDigest(ERPNextTestSuite):
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
