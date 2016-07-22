# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import fmt_money, formatdate, format_time, now_datetime, \
	get_url_to_form, get_url_to_list, flt
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from frappe.core.doctype.user.user import STANDARD_USERS
import frappe.desk.notifications
from erpnext.accounts.utils import get_balance_on

user_specific_content = ["calendar_events", "todo_list"]

from frappe.model.document import Document
class EmailDigest(Document):
	def __init__(self, arg1, arg2=None):
		super(EmailDigest, self).__init__(arg1, arg2)

		self.from_date, self.to_date = self.get_from_to_date()
		self.set_dates()
		self._accounts = {}
		self.currency = frappe.db.get_value("Company", self.company,
			"default_currency")

	def get_users(self):
		"""get list of users"""
		user_list = frappe.db.sql("""
			select name, enabled from tabUser
			where name not in ({})
			and user_type != "Website User"
			order by enabled desc, name asc""".format(", ".join(["%s"]*len(STANDARD_USERS))), STANDARD_USERS, as_dict=1)

		if self.recipient_list:
			recipient_list = self.recipient_list.split("\n")
		else:
			recipient_list = []
		for p in user_list:
			p["checked"] = p["name"] in recipient_list and 1 or 0

		frappe.response['user_list'] = user_list

	def send(self):
		# send email only to enabled users
		valid_users = [p[0] for p in frappe.db.sql("""select name from `tabUser`
			where enabled=1""")]
		recipients = filter(lambda r: r in valid_users,
			self.recipient_list.split("\n"))

		original_user = frappe.session.user

		if recipients:
			for user_id in recipients:
				frappe.set_user(user_id)
				msg_for_this_receipient = self.get_msg_html()
				if msg_for_this_receipient:
					frappe.sendmail(
						recipients=user_id,
						subject="{frequency} Digest".format(frequency=self.frequency),
						message=msg_for_this_receipient,
						reference_doctype = self.doctype,
						reference_name = self.name,
						unsubscribe_message = _("Unsubscribe from this Email Digest"))

		frappe.set_user(original_user)

	def get_msg_html(self):
		"""Build email digest content"""
		frappe.flags.ignore_account_permission = True
		from erpnext.setup.doctype.email_digest.quotes import get_random_quote

		context = frappe._dict()
		context.update(self.__dict__)

		self.set_title(context)
		self.set_style(context)
		self.set_accounting_cards(context)

		context.events = self.get_calendar_events()
		context.todo_list = self.get_todo_list()
		context.notifications = self.get_notifications()

		quote = get_random_quote()
		context.quote = {"text": quote[0], "author": quote[1]}

		if not (context.events or context.todo_list or context.notifications or context.cards):
			return None

		frappe.flags.ignore_account_permission = False

		# style
		return frappe.render_template("erpnext/setup/doctype/email_digest/templates/default.html",
			context, is_path=True)

	def set_title(self, context):
		"""Set digest title"""
		if self.frequency=="Daily":
			context.title = _("Daily Reminders")
			context.subtitle = _("Pending activities for today")
		elif self.frequency=="Weekly":
			context.title = _("This Week's Summary")
			context.subtitle = _("Summary for this week and pending activities")
		elif self.frequency=="Monthly":
			context.title = _("This Month's Summary")
			context.subtitle = _("Summary for this month and pending activities")

	def set_style(self, context):
		"""Set standard digest style"""
		context.text_muted = '#8D99A6'
		context.text_color = '#36414C'
		context.h1 = 'margin-bottom: 30px; margin-top: 40px; font-weight: 400; font-size: 30px;'
		context.h2 = 'margin-bottom: 30px; margin-top: -20px; font-weight: 400; font-size: 20px;'
		context.label_css = '''display: inline-block; color: {text_muted};
			padding: 3px 7px; margin-right: 7px;'''.format(text_muted = context.text_muted)
		context.section_head = 'margin-top: 60px; font-size: 16px;'
		context.line_item  = 'padding: 5px 0px; margin: 0; border-bottom: 1px solid #d1d8dd;'
		context.link_css = 'color: {text_color}; text-decoration: none;'.format(text_color = context.text_color)


	def get_notifications(self):
		"""Get notifications for user"""
		notifications = frappe.desk.notifications.get_notifications()

		notifications = sorted(notifications.get("open_count_doctype", {}).items(),
			lambda a, b: 1 if a[1] < b[1] else -1)

		notifications = [{"key": n[0], "value": n[1],
			"link": get_url_to_list(n[0])} for n in notifications if n[1]]

		return notifications

	def get_calendar_events(self):
		"""Get calendar events for given user"""
		from frappe.desk.doctype.event.event import get_events
		events = get_events(self.future_from_date.strftime("%Y-%m-%d"),
			self.future_to_date.strftime("%Y-%m-%d")) or []

		for i, e in enumerate(events):
			e.starts_on_label = format_time(e.starts_on)
			e.ends_on_label = format_time(e.ends_on) if e.ends_on else None
			e.date = formatdate(e.starts)
			e.link = get_url_to_form("Event", e.name)

		return events

	def get_todo_list(self, user_id=None):
		"""Get to-do list"""
		if not user_id:
			user_id = frappe.session.user

		todo_list = frappe.db.sql("""select *
			from `tabToDo` where (owner=%s or assigned_by=%s) and status="Open"
			order by field(priority, 'High', 'Medium', 'Low') asc, date asc limit 20""",
			(user_id, user_id), as_dict=True)

		for t in todo_list:
			t.link = get_url_to_form("ToDo", t.name)

		return todo_list

	def set_accounting_cards(self, context):
		"""Create accounting cards if checked"""

		cache = frappe.cache()
		context.cards = []
		for key in ("income", "expenses_booked", "income_year_to_date", "expense_year_to_date",
			"invoiced_amount", "payables", "bank_balance"):
			if self.get(key):
				cache_key = "email_digest:card:{0}:{1}".format(self.company, key)
				card = cache.get(cache_key)

				if card:
					card = eval(card)

				else:
					card = frappe._dict(getattr(self, "get_" + key)())

					# format values
					if card.last_value:
						card.diff = int(flt(card.value - card.last_value) / card.last_value * 100)
						if card.diff < 0:
							card.diff = str(card.diff)
							card.gain = False
						else:
							card.diff = "+" + str(card.diff)
							card.gain = True

						card.last_value = self.fmt_money(card.last_value)

					card.value = self.fmt_money(card.value)

					cache.setex(cache_key, card, 24 * 60 * 60)

				context.cards.append(card)

	def get_income(self):
		"""Get income for given period"""
		income, past_income = self.get_period_amounts(self.get_root_type_accounts("income"))

		return {
			"label": self.meta.get_label("income"),
			"value": income,
			"last_value": past_income
		}

	def get_income_year_to_date(self):
		"""Get income to date"""
		return self.get_year_to_date_balance("income")

	def get_expense_year_to_date(self):
		"""Get income to date"""
		return self.get_year_to_date_balance("expense")

	def get_year_to_date_balance(self, root_type):
		"""Get income to date"""
		balance = 0.0

		for account in self.get_root_type_accounts(root_type):
			balance += get_balance_on(account, date = self.future_to_date)

		return {
			"label": self.meta.get_label(root_type + "_year_to_date"),
			"value": balance
		}

	def get_bank_balance(self):
		# account is of type "Bank" or "Cash"
		return self.get_type_balance('bank_balance', 'Bank')

	def get_payables(self):
		return self.get_type_balance('payables', 'Payable')

	def get_invoiced_amount(self):
		return self.get_type_balance('invoiced_amount', 'Receivable')

	def get_expenses_booked(self):
		expense, past_expense = self.get_period_amounts(self.get_root_type_accounts("expense"))

		return {
			"label": self.meta.get_label("expenses_booked"),
			"value": expense,
			"last_value": past_expense
		}

	def get_period_amounts(self, accounts):
		"""Get amounts for current and past periods"""
		balance = past_balance = 0.0
		for account in accounts:
			balance += (get_balance_on(account, date = self.future_to_date)
				- get_balance_on(account, date = self.future_from_date))

			past_balance += (get_balance_on(account, date = self.past_to_date)
				- get_balance_on(account, date = self.past_from_date))

		return balance, past_balance

	def get_type_balance(self, fieldname, account_type):
		accounts = [d.name for d in \
			frappe.db.get_all("Account", filters={"account_type": account_type,
				"company": self.company, "is_group": 0})]

		balance = prev_balance = 0.0
		for account in accounts:
			balance += get_balance_on(account, date=self.future_from_date)
			prev_balance += get_balance_on(account, date=self.past_from_date)

		return {
			'label': self.meta.get_label(fieldname),
			'value': balance,
			'last_value': prev_balance
		}

	def get_root_type_accounts(self, root_type):
		if not root_type in self._accounts:
			self._accounts[root_type] = [d.name for d in \
				frappe.db.get_all("Account", filters={"root_type": root_type.title(),
					"company": self.company, "is_group": 0})]
		return self._accounts[root_type]

	def get_from_to_date(self):
		today = now_datetime().date()

		# decide from date based on email digest frequency
		if self.frequency == "Daily":
			# from date, to_date is yesterday
			from_date = to_date = today - timedelta(days=1)
		elif self.frequency == "Weekly":
			# from date is the previous week's monday
			from_date = today - timedelta(days=today.weekday(), weeks=1)

			# to date is sunday i.e. the previous day
			to_date = from_date + timedelta(days=6)
		else:
			# from date is the 1st day of the previous month
			from_date = today - relativedelta(days=today.day-1, months=1)
			# to date is the last day of the previous month
			to_date = today - relativedelta(days=today.day)

		return from_date, to_date

	def set_dates(self):
		self.future_from_date, self.future_to_date = self.from_date, self.to_date

		# decide from date based on email digest frequency
		if self.frequency == "Daily":
			self.past_from_date = self.past_to_date = self.future_from_date - relativedelta(days = 1)

		elif self.frequency == "Weekly":
			self.past_from_date = self.future_from_date - relativedelta(weeks=1)
			self.past_to_date = self.future_from_date - relativedelta(days=1)
		else:
			self.past_from_date = self.future_from_date - relativedelta(months=1)
			self.past_to_date = self.future_from_date - relativedelta(days=1)

	def get_next_sending(self):
		from_date, to_date = self.get_from_to_date()

		send_date = to_date + timedelta(days=1)

		if self.frequency == "Daily":
			next_send_date = send_date + timedelta(days=1)
		elif self.frequency == "Weekly":
			next_send_date = send_date + timedelta(weeks=1)
		else:
			next_send_date = send_date + relativedelta(months=1)
		self.next_send = formatdate(next_send_date) + " at midnight"

		return send_date

	def onload(self):
		self.get_next_sending()

	def fmt_money(self, value):
		return fmt_money(abs(value), currency = self.currency)

def send():
	now_date = now_datetime().date()

	for ed in frappe.db.sql("""select name from `tabEmail Digest`
			where enabled=1 and docstatus<2""", as_list=1):
		ed_obj = frappe.get_doc('Email Digest', ed[0])
		if (now_date == ed_obj.get_next_sending()):
			ed_obj.send()

@frappe.whitelist()
def get_digest_msg(name):
	return frappe.get_doc("Email Digest", name).get_msg_html()
