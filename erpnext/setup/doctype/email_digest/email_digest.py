# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from datetime import timedelta

import frappe
import frappe.desk.notifications
from dateutil.relativedelta import relativedelta
from frappe import _
from frappe.core.doctype.user.user import STANDARD_USERS
from frappe.utils import (
	add_to_date,
	flt,
	fmt_money,
	format_time,
	formatdate,
	get_link_to_report,
	get_url_to_form,
	get_url_to_list,
	now_datetime,
	today,
)

from erpnext.accounts.utils import get_balance_on, get_count_on, get_fiscal_year

user_specific_content = ["calendar_events", "todo_list"]

from frappe.model.document import Document


class EmailDigest(Document):
	def __init__(self, *args, **kwargs):
		super(EmailDigest, self).__init__(*args, **kwargs)

		self.from_date, self.to_date = self.get_from_to_date()
		self.set_dates()
		self._accounts = {}
		self.currency = frappe.db.get_value("Company", self.company, "default_currency")

	@frappe.whitelist()
	def get_users(self):
		"""get list of users"""
		user_list = frappe.db.sql(
			"""
			select name, enabled from tabUser
			where name not in ({})
			and user_type != "Website User"
			order by enabled desc, name asc""".format(
				", ".join(["%s"] * len(STANDARD_USERS))
			),
			STANDARD_USERS,
			as_dict=1,
		)

		if self.recipient_list:
			recipient_list = self.recipient_list.split("\n")
		else:
			recipient_list = []
		for p in user_list:
			p["checked"] = p["name"] in recipient_list and 1 or 0

		frappe.response["user_list"] = user_list

	@frappe.whitelist()
	def send(self):
		# send email only to enabled users
		valid_users = [
			p[0]
			for p in frappe.db.sql(
				"""select name from `tabUser`
			where enabled=1"""
			)
		]

		if self.recipients:
			for row in self.recipients:
				msg_for_this_recipient = self.get_msg_html()
				if msg_for_this_recipient and row.recipient in valid_users:
					frappe.sendmail(
						recipients=row.recipient,
						subject=_("{0} Digest").format(self.frequency),
						message=msg_for_this_recipient,
						reference_doctype=self.doctype,
						reference_name=self.name,
						unsubscribe_message=_("Unsubscribe from this Email Digest"),
					)

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

		if self.get("purchase_orders_items_overdue"):
			(
				context.purchase_order_list,
				context.purchase_orders_items_overdue_list,
			) = self.get_purchase_orders_items_overdue_list()
			if not context.purchase_order_list:
				frappe.throw(_("No items to be received are overdue"))

		if not context:
			return None

		frappe.flags.ignore_account_permission = False

		# style
		return frappe.render_template(
			"erpnext/setup/doctype/email_digest/templates/default.html", context, is_path=True
		)

	def set_title(self, context):
		"""Set digest title"""
		if self.frequency == "Daily":
			context.title = _("Daily Reminders")
			context.subtitle = _("Pending activities for today")
		elif self.frequency == "Weekly":
			context.title = _("This Week's Summary")
			context.subtitle = _("Summary for this week and pending activities")
		elif self.frequency == "Monthly":
			context.title = _("This Month's Summary")
			context.subtitle = _("Summary for this month and pending activities")

	def set_style(self, context):
		"""Set standard digest style"""
		context.text_muted = "#8D99A6"
		context.text_color = "#36414C"
		context.h1 = "margin-bottom: 30px; margin-top: 40px; font-weight: 400; font-size: 30px;"
		context.h2 = "margin-bottom: 30px; margin-top: -20px; font-weight: 400; font-size: 20px;"
		context.label_css = """display: inline-block; color: {text_muted};
			padding: 3px 7px; margin-right: 7px;""".format(
			text_muted=context.text_muted
		)
		context.section_head = "margin-top: 60px; font-size: 16px;"
		context.line_item = "padding: 5px 0px; margin: 0; border-bottom: 1px solid #d1d8dd;"
		context.link_css = "color: {text_color}; text-decoration: none;".format(
			text_color=context.text_color
		)

	def get_notifications(self):
		"""Get notifications for user"""
		notifications = frappe.desk.notifications.get_notifications()

		notifications = sorted(notifications.get("open_count_doctype", {}).items(), key=lambda a: a[1])

		notifications = [
			{"key": n[0], "value": n[1], "link": get_url_to_list(n[0])} for n in notifications if n[1]
		]

		return notifications

	def get_calendar_events(self):
		"""Get calendar events for given user"""
		from frappe.desk.doctype.event.event import get_events

		from_date, to_date = get_future_date_for_calendaer_event(self.frequency)

		events = get_events(from_date, to_date)

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

		todo_list = frappe.db.sql(
			"""select *
			from `tabToDo` where (owner=%s or assigned_by=%s) and status="Open"
			order by field(priority, 'High', 'Medium', 'Low') asc, date asc limit 20""",
			(user_id, user_id),
			as_dict=True,
		)

		for t in todo_list:
			t.link = get_url_to_form("ToDo", t.name)

		return todo_list

	def get_todo_count(self, user_id=None):
		"""Get count of Todo"""
		if not user_id:
			user_id = frappe.session.user

		return frappe.db.sql(
			"""select count(*) from `tabToDo`
			where status='Open' and (owner=%s or assigned_by=%s)""",
			(user_id, user_id),
		)[0][0]

	def get_issue_list(self, user_id=None):
		"""Get issue list"""
		if not user_id:
			user_id = frappe.session.user

		meta = frappe.get_meta("Issue")
		role_permissions = frappe.permissions.get_role_permissions(meta, user_id)
		if not role_permissions.get("read"):
			return None

		issue_list = frappe.db.sql(
			"""select *
			from `tabIssue` where status in ("Replied","Open")
			order by modified asc limit 10""",
			as_dict=True,
		)

		for t in issue_list:
			t.link = get_url_to_form("Issue", t.name)

		return issue_list

	def get_issue_count(self):
		"""Get count of Issue"""
		return frappe.db.sql(
			"""select count(*) from `tabIssue`
			where status in ('Open','Replied') """
		)[0][0]

	def get_project_list(self, user_id=None):
		"""Get project list"""
		if not user_id:
			user_id = frappe.session.user

		project_list = frappe.db.sql(
			"""select *
			from `tabProject` where status='Open' and project_type='External'
			order by modified asc limit 10""",
			as_dict=True,
		)

		for t in project_list:
			t.link = get_url_to_form("Issue", t.name)

		return project_list

	def get_project_count(self):
		"""Get count of Project"""
		return frappe.db.sql(
			"""select count(*) from `tabProject`
			where status='Open' and project_type='External'"""
		)[0][0]

	def set_accounting_cards(self, context):
		"""Create accounting cards if checked"""

		cache = frappe.cache()
		context.cards = []
		for key in (
			"income",
			"expenses_booked",
			"income_year_to_date",
			"expense_year_to_date",
			"bank_balance",
			"credit_balance",
			"invoiced_amount",
			"payables",
			"sales_orders_to_bill",
			"purchase_orders_to_bill",
			"sales_order",
			"purchase_order",
			"sales_orders_to_deliver",
			"purchase_orders_to_receive",
			"sales_invoice",
			"purchase_invoice",
			"new_quotations",
			"pending_quotations",
		):

			if self.get(key):
				cache_key = "email_digest:card:{0}:{1}:{2}:{3}".format(
					self.company, self.frequency, key, self.from_date
				)
				card = cache.get(cache_key)

				if card:
					card = frappe.safe_eval(card)

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
						card.last_value = self.fmt_money(
							card.last_value, False if key in ("bank_balance", "credit_balance") else True
						)

					if card.billed_value:
						card.billed = int(flt(card.billed_value) / card.value * 100)
						card.billed = "% Billed " + str(card.billed)

					if card.delivered_value:
						card.delivered = int(flt(card.delivered_value) / card.value * 100)
						if key == "pending_sales_orders":
							card.delivered = "% Delivered " + str(card.delivered)
						else:
							card.delivered = "% Received " + str(card.delivered)

					if key == "credit_balance":
						card.value = card.value * -1
					card.value = self.fmt_money(
						card.value, False if key in ("bank_balance", "credit_balance") else True
					)

					cache.set_value(cache_key, card, expires_in_sec=24 * 60 * 60)

				context.cards.append(card)

	def get_income(self):
		"""Get income for given period"""
		income, past_income, count = self.get_period_amounts(self.get_roots("income"), "income")

		income_account = frappe.db.get_all(
			"Account",
			fields=["name"],
			filters={"root_type": "Income", "parent_account": "", "company": self.company},
		)

		label = get_link_to_report(
			"General Ledger",
			self.meta.get_label("income"),
			filters={
				"from_date": self.future_from_date,
				"to_date": self.future_to_date,
				"account": income_account[0].name,
				"company": self.company,
			},
		)
		return {"label": label, "value": income, "last_value": past_income, "count": count}

	def get_income_year_to_date(self):
		"""Get income to date"""
		return self.get_year_to_date_balance("income", "income")

	def get_expense_year_to_date(self):
		"""Get income to date"""
		return self.get_year_to_date_balance("expense", "expenses_booked")

	def get_year_to_date_balance(self, root_type, fieldname):
		"""Get income to date"""
		balance = 0.0
		count = 0

		for account in self.get_root_type_accounts(root_type):
			balance += get_balance_on(account, date=self.future_to_date)
			count += get_count_on(account, fieldname, date=self.future_to_date)

		if fieldname == "income":
			filters = {"currency": self.currency}
			label = get_link_to_report(
				"Profit and Loss Statement",
				label=self.meta.get_label(root_type + "_year_to_date"),
				filters=filters,
			)

		elif fieldname == "expenses_booked":
			filters = {"currency": self.currency}
			label = get_link_to_report(
				"Profit and Loss Statement",
				label=self.meta.get_label(root_type + "_year_to_date"),
				filters=filters,
			)

		return {"label": label, "value": balance, "count": count}

	def get_bank_balance(self):
		# account is of type "Bank" and root_type is Asset
		return self.get_type_balance("bank_balance", "Bank", root_type="Asset")

	def get_credit_balance(self):
		# account is of type "Bank" and root_type is Liability
		return self.get_type_balance("credit_balance", "Bank", root_type="Liability")

	def get_payables(self):
		return self.get_type_balance("payables", "Payable")

	def get_invoiced_amount(self):
		return self.get_type_balance("invoiced_amount", "Receivable")

	def get_expenses_booked(self):
		expenses, past_expenses, count = self.get_period_amounts(
			self.get_roots("expense"), "expenses_booked"
		)

		expense_account = frappe.db.get_all(
			"Account",
			fields=["name"],
			filters={"root_type": "Expense", "parent_account": "", "company": self.company},
		)

		label = get_link_to_report(
			"General Ledger",
			self.meta.get_label("expenses_booked"),
			filters={
				"company": self.company,
				"from_date": self.future_from_date,
				"to_date": self.future_to_date,
				"account": expense_account[0].name,
			},
		)
		return {"label": label, "value": expenses, "last_value": past_expenses, "count": count}

	def get_period_amounts(self, accounts, fieldname):
		"""Get amounts for current and past periods"""
		balance = past_balance = 0.0
		count = 0
		for account in accounts:
			balance += get_incomes_expenses_for_period(account, self.future_from_date, self.future_to_date)
			past_balance += get_incomes_expenses_for_period(account, self.past_from_date, self.past_to_date)
			count += get_count_for_period(account, fieldname, self.future_from_date, self.future_to_date)

		return balance, past_balance, count

	def get_sales_orders_to_bill(self):
		"""Get value not billed"""

		value, count = frappe.db.sql(
			"""select ifnull((sum(grand_total)) - (sum(grand_total*per_billed/100)),0),
                    count(*) from `tabSales Order`
					where (transaction_date <= %(to_date)s) and billing_status != "Fully Billed" and company = %(company)s
					and status not in ('Closed','Cancelled', 'Completed') """,
			{"to_date": self.future_to_date, "company": self.company},
		)[0]

		label = get_link_to_report(
			"Sales Order",
			label=self.meta.get_label("sales_orders_to_bill"),
			report_type="Report Builder",
			doctype="Sales Order",
			filters={
				"status": [["!=", "Closed"], ["!=", "Cancelled"]],
				"per_billed": [["<", 100]],
				"transaction_date": [["<=", self.future_to_date]],
				"company": self.company,
			},
		)

		return {"label": label, "value": value, "count": count}

	def get_sales_orders_to_deliver(self):
		"""Get value not delivered"""

		value, count = frappe.db.sql(
			"""select ifnull((sum(grand_total)) - (sum(grand_total*per_delivered/100)),0),
					count(*) from `tabSales Order`
					where (transaction_date <= %(to_date)s) and delivery_status != "Fully Delivered" and company = %(company)s
					and status not in ('Closed','Cancelled', 'Completed') """,
			{"to_date": self.future_to_date, "company": self.company},
		)[0]

		label = get_link_to_report(
			"Sales Order",
			label=self.meta.get_label("sales_orders_to_deliver"),
			report_type="Report Builder",
			doctype="Sales Order",
			filters={
				"status": [["!=", "Closed"], ["!=", "Cancelled"], ["!=", "Completed"]],
				"delivery_status": [["!=", "Fully Delivered"]],
				"transaction_date": [["<=", self.future_to_date]],
				"company": self.company,
			},
		)

		return {"label": label, "value": value, "count": count}

	def get_purchase_orders_to_receive(self):
		"""Get value not received"""

		value, count = frappe.db.sql(
			"""select ifnull((sum(grand_total))-(sum(grand_total*per_received/100)),0),
                    count(*) from `tabPurchase Order`
					where (transaction_date <= %(to_date)s) and per_received < 100 and company = %(company)s
					and status not in ('Closed','Cancelled', 'Completed') """,
			{"to_date": self.future_to_date, "company": self.company},
		)[0]

		label = get_link_to_report(
			"Purchase Order",
			label=self.meta.get_label("purchase_orders_to_receive"),
			report_type="Report Builder",
			doctype="Purchase Order",
			filters={
				"status": [["!=", "Closed"], ["!=", "Cancelled"], ["!=", "Completed"]],
				"per_received": [["<", 100]],
				"transaction_date": [["<=", self.future_to_date]],
				"company": self.company,
			},
		)

		return {"label": label, "value": value, "count": count}

	def get_purchase_orders_to_bill(self):
		"""Get purchase not billed"""

		value, count = frappe.db.sql(
			"""select ifnull((sum(grand_total)) - (sum(grand_total*per_billed/100)),0),
                    count(*) from `tabPurchase Order`
					where (transaction_date <= %(to_date)s) and per_billed < 100 and company = %(company)s
					and status not in ('Closed','Cancelled', 'Completed') """,
			{"to_date": self.future_to_date, "company": self.company},
		)[0]

		label = get_link_to_report(
			"Purchase Order",
			label=self.meta.get_label("purchase_orders_to_bill"),
			report_type="Report Builder",
			doctype="Purchase Order",
			filters={
				"status": [["!=", "Closed"], ["!=", "Cancelled"], ["!=", "Completed"]],
				"per_received": [["<", 100]],
				"transaction_date": [["<=", self.future_to_date]],
				"company": self.company,
			},
		)

		return {"label": label, "value": value, "count": count}

	def get_type_balance(self, fieldname, account_type, root_type=None):

		if root_type:
			accounts = [
				d.name
				for d in frappe.db.get_all(
					"Account",
					filters={
						"account_type": account_type,
						"company": self.company,
						"is_group": 0,
						"root_type": root_type,
					},
				)
			]
		else:
			accounts = [
				d.name
				for d in frappe.db.get_all(
					"Account", filters={"account_type": account_type, "company": self.company, "is_group": 0}
				)
			]

		balance = prev_balance = 0.0
		count = 0
		for account in accounts:
			balance += get_balance_on(account, date=self.future_to_date, in_account_currency=False)
			count += get_count_on(account, fieldname, date=self.future_to_date)
			prev_balance += get_balance_on(account, date=self.past_to_date, in_account_currency=False)

		if fieldname in ("bank_balance", "credit_balance"):
			label = ""
			if fieldname == "bank_balance":
				filters = {
					"root_type": "Asset",
					"account_type": "Bank",
					"report_date": self.future_to_date,
					"company": self.company,
				}
				label = get_link_to_report(
					"Account Balance", label=self.meta.get_label(fieldname), filters=filters
				)
			else:
				filters = {
					"root_type": "Liability",
					"account_type": "Bank",
					"report_date": self.future_to_date,
					"company": self.company,
				}
				label = get_link_to_report(
					"Account Balance", label=self.meta.get_label(fieldname), filters=filters
				)

			return {"label": label, "value": balance, "last_value": prev_balance}
		else:
			if account_type == "Payable":
				label = get_link_to_report(
					"Accounts Payable",
					label=self.meta.get_label(fieldname),
					filters={"report_date": self.future_to_date, "company": self.company},
				)
			elif account_type == "Receivable":
				label = get_link_to_report(
					"Accounts Receivable",
					label=self.meta.get_label(fieldname),
					filters={"report_date": self.future_to_date, "company": self.company},
				)
			else:
				label = self.meta.get_label(fieldname)

			return {"label": label, "value": balance, "last_value": prev_balance, "count": count}

	def get_roots(self, root_type):
		return [
			d.name
			for d in frappe.db.get_all(
				"Account",
				filters={
					"root_type": root_type.title(),
					"company": self.company,
					"is_group": 1,
					"parent_account": ["in", ("", None)],
				},
			)
		]

	def get_root_type_accounts(self, root_type):
		if not root_type in self._accounts:
			self._accounts[root_type] = [
				d.name
				for d in frappe.db.get_all(
					"Account", filters={"root_type": root_type.title(), "company": self.company, "is_group": 0}
				)
			]
		return self._accounts[root_type]

	def get_purchase_order(self):

		return self.get_summary_of_doc("Purchase Order", "purchase_order")

	def get_sales_order(self):

		return self.get_summary_of_doc("Sales Order", "sales_order")

	def get_pending_purchase_orders(self):

		return self.get_summary_of_pending("Purchase Order", "pending_purchase_orders", "per_received")

	def get_pending_sales_orders(self):

		return self.get_summary_of_pending("Sales Order", "pending_sales_orders", "per_delivered")

	def get_sales_invoice(self):

		return self.get_summary_of_doc("Sales Invoice", "sales_invoice")

	def get_purchase_invoice(self):

		return self.get_summary_of_doc("Purchase Invoice", "purchase_invoice")

	def get_new_quotations(self):

		return self.get_summary_of_doc("Quotation", "new_quotations")

	def get_pending_quotations(self):

		return self.get_summary_of_pending_quotations("pending_quotations")

	def get_summary_of_pending(self, doc_type, fieldname, getfield):

		value, count, billed_value, delivered_value = frappe.db.sql(
			"""select ifnull(sum(grand_total),0), count(*),
			ifnull(sum(grand_total*per_billed/100),0), ifnull(sum(grand_total*{0}/100),0)  from `tab{1}`
			where (transaction_date <= %(to_date)s)
			and status not in ('Closed','Cancelled', 'Completed')
			and company = %(company)s """.format(
				getfield, doc_type
			),
			{"to_date": self.future_to_date, "company": self.company},
		)[0]

		return {
			"label": self.meta.get_label(fieldname),
			"value": value,
			"billed_value": billed_value,
			"delivered_value": delivered_value,
			"count": count,
		}

	def get_summary_of_pending_quotations(self, fieldname):

		value, count = frappe.db.sql(
			"""select ifnull(sum(grand_total),0), count(*) from `tabQuotation`
			where (transaction_date <= %(to_date)s)
			and company = %(company)s
			and status not in ('Ordered','Cancelled', 'Lost') """,
			{"to_date": self.future_to_date, "company": self.company},
		)[0]

		last_value = frappe.db.sql(
			"""select ifnull(sum(grand_total),0) from `tabQuotation`
			where (transaction_date <= %(to_date)s)
			and company = %(company)s
			and status not in ('Ordered','Cancelled', 'Lost') """,
			{"to_date": self.past_to_date, "company": self.company},
		)[0][0]

		label = get_link_to_report(
			"Quotation",
			label=self.meta.get_label(fieldname),
			report_type="Report Builder",
			doctype="Quotation",
			filters={
				"status": [["!=", "Ordered"], ["!=", "Cancelled"], ["!=", "Lost"]],
				"per_received": [["<", 100]],
				"transaction_date": [["<=", self.future_to_date]],
				"company": self.company,
			},
		)

		return {"label": label, "value": value, "last_value": last_value, "count": count}

	def get_summary_of_doc(self, doc_type, fieldname):

		date_field = (
			"posting_date" if doc_type in ["Sales Invoice", "Purchase Invoice"] else "transaction_date"
		)

		value = flt(
			self.get_total_on(doc_type, self.future_from_date, self.future_to_date)[0].grand_total
		)
		count = self.get_total_on(doc_type, self.future_from_date, self.future_to_date)[0].count

		last_value = flt(
			self.get_total_on(doc_type, self.past_from_date, self.past_to_date)[0].grand_total
		)

		filters = {
			date_field: [[">=", self.future_from_date], ["<=", self.future_to_date]],
			"status": [["!=", "Cancelled"]],
			"company": self.company,
		}

		label = get_link_to_report(
			doc_type,
			label=self.meta.get_label(fieldname),
			report_type="Report Builder",
			filters=filters,
			doctype=doc_type,
		)

		return {"label": label, "value": value, "last_value": last_value, "count": count}

	def get_total_on(self, doc_type, from_date, to_date):

		date_field = (
			"posting_date" if doc_type in ["Sales Invoice", "Purchase Invoice"] else "transaction_date"
		)

		return frappe.get_all(
			doc_type,
			filters={
				date_field: ["between", (from_date, to_date)],
				"status": ["not in", ("Cancelled")],
				"company": self.company,
			},
			fields=["count(*) as count", "sum(grand_total) as grand_total"],
		)

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
			from_date = today - relativedelta(days=today.day - 1, months=1)
			# to date is the last day of the previous month
			to_date = today - relativedelta(days=today.day)

		return from_date, to_date

	def set_dates(self):
		self.future_from_date, self.future_to_date = self.from_date, self.to_date

		# decide from date based on email digest frequency
		if self.frequency == "Daily":
			self.past_from_date = self.past_to_date = self.future_from_date - relativedelta(days=1)

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

	def fmt_money(self, value, absol=True):
		if absol:
			return fmt_money(abs(value), currency=self.currency)
		else:
			return fmt_money(value, currency=self.currency)

	def get_purchase_orders_items_overdue_list(self):
		fields_po = "distinct `tabPurchase Order Item`.parent as po"
		fields_poi = (
			"`tabPurchase Order Item`.parent, `tabPurchase Order Item`.schedule_date, item_code,"
			"received_qty, qty - received_qty as missing_qty, rate, amount"
		)

		sql_po = """select {fields} from `tabPurchase Order Item`
			left join `tabPurchase Order` on `tabPurchase Order`.name = `tabPurchase Order Item`.parent
			where status<>'Closed' and `tabPurchase Order Item`.docstatus=1 and CURRENT_DATE > `tabPurchase Order Item`.schedule_date
			and received_qty < qty order by `tabPurchase Order Item`.parent DESC,
			`tabPurchase Order Item`.schedule_date DESC""".format(
			fields=fields_po
		)

		sql_poi = """select {fields} from `tabPurchase Order Item`
			left join `tabPurchase Order` on `tabPurchase Order`.name = `tabPurchase Order Item`.parent
			where status<>'Closed' and `tabPurchase Order Item`.docstatus=1 and CURRENT_DATE > `tabPurchase Order Item`.schedule_date
			and received_qty < qty order by `tabPurchase Order Item`.idx""".format(
			fields=fields_poi
		)
		purchase_order_list = frappe.db.sql(sql_po, as_dict=True)
		purchase_order_items_overdue_list = frappe.db.sql(sql_poi, as_dict=True)

		for t in purchase_order_items_overdue_list:
			t.link = get_url_to_form("Purchase Order", t.parent)
			t.rate = fmt_money(t.rate, 2, t.currency)
			t.amount = fmt_money(t.amount, 2, t.currency)
		return purchase_order_list, purchase_order_items_overdue_list


def send():
	now_date = now_datetime().date()

	for ed in frappe.db.sql(
		"""select name from `tabEmail Digest`
			where enabled=1 and docstatus<2""",
		as_list=1,
	):
		ed_obj = frappe.get_doc("Email Digest", ed[0])
		if now_date == ed_obj.get_next_sending():
			ed_obj.send()


@frappe.whitelist()
def get_digest_msg(name):
	return frappe.get_doc("Email Digest", name).get_msg_html()


def get_incomes_expenses_for_period(account, from_date, to_date):
	"""Get amounts for current and past periods"""

	val = 0.0
	balance_on_to_date = get_balance_on(account, date=to_date)
	balance_before_from_date = get_balance_on(account, date=from_date - timedelta(days=1))

	fy_start_date = get_fiscal_year(to_date)[1]

	if from_date == fy_start_date:
		val = balance_on_to_date
	elif from_date > fy_start_date:
		val = balance_on_to_date - balance_before_from_date
	else:
		last_year_closing_balance = get_balance_on(account, date=fy_start_date - timedelta(days=1))
		val = balance_on_to_date + (last_year_closing_balance - balance_before_from_date)

	return val


def get_count_for_period(account, fieldname, from_date, to_date):
	count = 0.0
	count_on_to_date = get_count_on(account, fieldname, to_date)
	count_before_from_date = get_count_on(account, fieldname, from_date - timedelta(days=1))

	fy_start_date = get_fiscal_year(to_date)[1]
	if from_date == fy_start_date:
		count = count_on_to_date
	elif from_date > fy_start_date:
		count = count_on_to_date - count_before_from_date
	else:
		last_year_closing_count = get_count_on(account, fieldname, fy_start_date - timedelta(days=1))
		count = count_on_to_date + (last_year_closing_count - count_before_from_date)

	return count


def get_future_date_for_calendaer_event(frequency):
	from_date = to_date = today()

	if frequency == "Weekly":
		to_date = add_to_date(from_date, weeks=1)
	elif frequency == "Monthly":
		to_date = add_to_date(from_date, months=1)

	return from_date, to_date
