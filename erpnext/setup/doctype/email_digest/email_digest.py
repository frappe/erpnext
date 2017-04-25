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
from erpnext.accounts.utils import get_balance_on, get_count_on

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
		
		if self.get("calendar_events"):
			context.events, context.event_count = self.get_calendar_events()
		if self.get("todo_list"):
			context.todo_list = self.get_todo_list()
			context.todo_count = self.get_todo_count()
		if self.get("notifications"):
			context.notifications = self.get_notifications()
		if self.get("issue"):
			context.issue_list = self.get_issue_list()
			context.issue_count = self.get_issue_count()
		if self.get("project"):
			context.project_list = self.get_project_list()
			context.project_count = self.get_project_count()

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
		
		event_count = 0
		for i, e in enumerate(events):
			e.starts_on_label = format_time(e.starts_on)
			e.ends_on_label = format_time(e.ends_on) if e.ends_on else None
			e.date = formatdate(e.starts)
			e.link = get_url_to_form("Event", e.name)
			event_count += 1

		return events, event_count

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
	
	def get_todo_count(self, user_id=None):
		"""Get count of Todo"""
		if not user_id:
			user_id = frappe.session.user

		return frappe.db.sql("""select count(*) from `tabToDo` 
			where status='Open' and (owner=%s or assigned_by=%s)""",
			(user_id, user_id))[0][0]

	def get_issue_list(self, user_id=None):
		"""Get issue list"""
		if not user_id:
			user_id = frappe.session.user
		
		meta = frappe.get_meta("Issue")
		role_permissions = frappe.permissions.get_role_permissions(meta, user_id)
		if not role_permissions.get("read"):
			return None

		issue_list = frappe.db.sql("""select *
			from `tabIssue` where status in ("Replied","Open")
			order by modified asc limit 10""", as_dict=True)

		for t in issue_list:
			t.link = get_url_to_form("Issue", t.name)

		return issue_list
	
	def get_issue_count(self):
		"""Get count of Issue"""
		return frappe.db.sql("""select count(*) from `tabIssue`
			where status in ('Open','Replied') """)[0][0]

	def get_project_list(self, user_id=None):
		"""Get project list"""
		if not user_id:
			user_id = frappe.session.user

		project_list = frappe.db.sql("""select *
			from `tabProject` where status='Open' and project_type='External'
			order by modified asc limit 10""", as_dict=True)

		for t in project_list:
			t.link = get_url_to_form("Issue", t.name)

		return project_list

	def get_project_count(self):
		"""Get count of Project"""
		return frappe.db.sql("""select count(*) from `tabProject`
			where status='Open' and project_type='External'""")[0][0]

	def set_accounting_cards(self, context):
		"""Create accounting cards if checked"""

		cache = frappe.cache()
		context.cards = []
		for key in ("income", "expenses_booked", "income_year_to_date","expense_year_to_date",
			 "new_quotations","pending_quotations","sales_order","purchase_order","pending_sales_orders","pending_purchase_orders",
			"invoiced_amount", "payables", "bank_balance", "credit_balance"):
			if self.get(key):
				cache_key = "email_digest:card:{0}:{1}:{2}".format(self.company, self.frequency, key)
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

						if key == "credit_balance":
							card.last_value = card.last_value * -1
						card.last_value = self.fmt_money(card.last_value,False if key in ("bank_balance", "credit_balance") else True)


					if card.billed_value:
						card.billed = int(flt(card.billed_value) / card.value * 100)
						card.billed = "% Billed " + str(card.billed)

					if card.delivered_value:
						card.delivered = int(flt(card.delivered_value) / card.value * 100)
						if key == "pending_sales_orders":
							card.delivered = "% Delivered " + str(card.delivered)
						else:
							card.delivered = "% Received " + str(card.delivered)
						
					if key =="credit_balance":
						card.value = card.value *-1
					card.value = self.fmt_money(card.value,False if key in ("bank_balance", "credit_balance") else True)

					cache.setex(cache_key, card, 24 * 60 * 60)

				context.cards.append(card)

	def get_income(self):
		"""Get income for given period"""
		income, past_income, count = self.get_period_amounts(self.get_root_type_accounts("income"),'income')

		return {
			"label": self.meta.get_label("income"),
			"value": income,
			"last_value": past_income,
			"count": count
		}

	def get_income_year_to_date(self):
		"""Get income to date"""
		return self.get_year_to_date_balance("income", "income")

	def get_expense_year_to_date(self):
		"""Get income to date"""
		return self.get_year_to_date_balance("expense","expenses_booked")

	def get_year_to_date_balance(self, root_type, fieldname):
		"""Get income to date"""
		balance = 0.0
		count = 0

		for account in self.get_root_type_accounts(root_type):
			balance += get_balance_on(account, date = self.future_to_date)
			count += get_count_on(account, fieldname, date = self.future_to_date)

		return {
			"label": self.meta.get_label(root_type + "_year_to_date"),
			"value": balance,
			"count": count
		}

	def get_bank_balance(self):
		# account is of type "Bank" and root_type is Asset
		return self.get_type_balance('bank_balance', 'Bank', root_type='Asset')
	
	def get_credit_balance(self):
		# account is of type "Bank" and root_type is Liability
		return self.get_type_balance('credit_balance', 'Bank', root_type='Liability')

	def get_payables(self):
		return self.get_type_balance('payables', 'Payable')

	def get_invoiced_amount(self):
		return self.get_type_balance('invoiced_amount', 'Receivable')

	def get_expenses_booked(self):
		expense, past_expense, count = self.get_period_amounts(self.get_root_type_accounts("expense"), 'expenses_booked')

		return {
			"label": self.meta.get_label("expenses_booked"),
			"value": expense,
			"last_value": past_expense,
			"count": count
		}

	def get_period_amounts(self, accounts, fieldname):
		"""Get amounts for current and past periods"""
		balance = past_balance = 0.0
		count = 0
		for account in accounts:
			balance += (get_balance_on(account, date = self.future_to_date)
				- get_balance_on(account, date = self.future_from_date - timedelta(days=1)))

			count += (get_count_on(account,fieldname, date = self.future_to_date )
				- get_count_on(account,fieldname, date = self.future_from_date - timedelta(days=1)))

			past_balance += (get_balance_on(account, date = self.past_to_date)
				- get_balance_on(account, date = self.past_from_date - timedelta(days=1)))

		return balance, past_balance, count

	def get_type_balance(self, fieldname, account_type, root_type=None):
		
		if root_type:
			accounts = [d.name for d in \
				frappe.db.get_all("Account", filters={"account_type": account_type,
				"company": self.company, "is_group": 0, "root_type": root_type})]
		else:
			accounts = [d.name for d in \
				frappe.db.get_all("Account", filters={"account_type": account_type,
				"company": self.company, "is_group": 0})]

		balance = prev_balance = 0.0
		count = 0
		for account in accounts:
			balance += get_balance_on(account, date=self.future_to_date)
			count += get_count_on(account, fieldname, date=self.future_to_date)
			prev_balance += get_balance_on(account, date=self.past_to_date)
		
		if fieldname in ("bank_balance","credit_balance"):
			return {
				'label': self.meta.get_label(fieldname),
				'value': balance,
				'last_value': prev_balance			}
		else:
			return {
				'label': self.meta.get_label(fieldname),
				'value': balance,
				'last_value': prev_balance,
				'count': count
			}
	

	def get_root_type_accounts(self, root_type):
		if not root_type in self._accounts:
			self._accounts[root_type] = [d.name for d in \
				frappe.db.get_all("Account", filters={"root_type": root_type.title(),
					"company": self.company, "is_group": 0})]
		return self._accounts[root_type]

	def get_purchase_order(self):
		
		return self.get_summary_of_doc("Purchase Order","purchase_order")

	def get_sales_order(self):

		return self.get_summary_of_doc("Sales Order","sales_order")
    
	def get_pending_purchase_orders(self):

		return self.get_summary_of_pending("Purchase Order","pending_purchase_orders","per_received")

	def get_pending_sales_orders(self):

		return self.get_summary_of_pending("Sales Order","pending_sales_orders","per_delivered")

	def get_new_quotations(self):

		return self.get_summary_of_doc("Quotation","new_quotations")

	def get_pending_quotations(self):

		return self.get_summary_of_pending_quotations("pending_quotations")
	
	def get_summary_of_pending(self, doc_type, fieldname, getfield):

		value, count, billed_value, delivered_value = frappe.db.sql("""select ifnull(sum(grand_total),0), count(*), 
			ifnull(sum(grand_total*per_billed/100),0), ifnull(sum(grand_total*{0}/100),0)  from `tab{1}`
			where (transaction_date <= %(to_date)s)
			and status not in ('Closed','Cancelled', 'Completed') """.format(getfield, doc_type),
			{"to_date": self.future_to_date})[0]
		
		return {
			"label": self.meta.get_label(fieldname),
            		"value": value,
			"billed_value": billed_value,
			"delivered_value": delivered_value,
            		"count": count
		}
	
	def get_summary_of_pending_quotations(self, fieldname):

		value, count = frappe.db.sql("""select ifnull(sum(grand_total),0), count(*) from `tabQuotation`
			where (transaction_date <= %(to_date)s)
			and status not in ('Ordered','Cancelled', 'Lost') """,{"to_date": self.future_to_date})[0]

		last_value = frappe.db.sql("""select ifnull(sum(grand_total),0) from `tabQuotation`
			where (transaction_date <= %(to_date)s)
			and status not in ('Ordered','Cancelled', 'Lost') """,{"to_date": self.past_to_date})[0][0]
		
		return {
			"label": self.meta.get_label(fieldname),
            		"value": value,
			"last_value": last_value,
            		"count": count
		}

	def get_summary_of_doc(self, doc_type, fieldname):
		
		value = self.get_total_on(doc_type, self.future_from_date, self.future_to_date)[0]
		count = self.get_total_on(doc_type, self.future_from_date, self.future_to_date)[1] 

		last_value =self.get_total_on(doc_type, self.past_from_date, self.past_to_date)[0]

		return {
			"label": self.meta.get_label(fieldname),
            		"value": value,
            		"last_value": last_value,
			"count": count
		}
	
	def get_total_on(self, doc_type, from_date, to_date):
		
		return frappe.db.sql("""select ifnull(sum(grand_total),0), count(*) from `tab{0}`
			where (transaction_date between %(from_date)s and %(to_date)s) and status not in ('Cancelled')""".format(doc_type),
			{"from_date": from_date, "to_date": to_date})[0]

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

	def fmt_money(self, value,absol=True):
		if absol:
			return fmt_money(abs(value), currency = self.currency)
		else:
			return fmt_money(value, currency=self.currency)

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
