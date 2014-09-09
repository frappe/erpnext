# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import fmt_money, formatdate, now_datetime, cstr, esc, \
	get_url_to_form, get_fullname
from frappe.utils.dateutils import datetime_in_user_format
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from frappe.utils.email_lib import sendmail
from frappe.core.doctype.user.user import STANDARD_USERS

content_sequence = [
	["Income / Expenses", ["income_year_to_date", "income", "expenses_booked"]],
	["Receivables / Payables", ["collections", "payments",
		"invoiced_amount", "payables"]],
	["Bank Balance", ["bank_balance"]],
	["Buying", ["new_purchase_requests", "new_supplier_quotations", "new_purchase_orders"]],
	["Selling", ["new_leads", "new_enquiries", "new_quotations", "new_sales_orders"]],
	["Stock", ["new_delivery_notes",  "new_purchase_receipts", "new_stock_entries"]],
	["Support", ["new_communications", "new_support_tickets", "open_tickets"]],
	["Projects", ["new_projects"]],
	["System", ["scheduler_errors"]],
]

user_specific_content = ["calendar_events", "todo_list"]

digest_template = """<style>p.ed-indent { margin-right: 17px; }</style>
<h2>%(name)s</h2>
<h4>%(company)s</h4>
<p style='color: grey'>%(date)s</p>
<hr>
%(with_value)s
%(no_value)s
<hr>
<p style="color: #888; font-size: 90%%">To change what you see here,
create more digests, go to Setup > Email Digest</p>"""

row_template = """<p style="%(style)s">
<span>%(label)s</span>:
<span style="font-weight: bold; font-size: 110%%">
	<span style="color: grey">%(currency)s</span>%(value)s
</span></p>"""

from frappe.model.document import Document
class EmailDigest(Document):
	def __init__(self, arg1, arg2=None):
		super(EmailDigest, self).__init__(arg1, arg2)
		self.from_date, self.to_date = self.get_from_to_date()
		self.future_from_date, self.future_to_date = self.get_future_from_to_date()
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

		common_msg = self.get_common_content()
		if recipients:
			for user_id in recipients:
				msg_for_this_receipient = self.get_msg_html(self.get_user_specific_content(user_id) + \
					common_msg)
				if msg_for_this_receipient:
					sendmail(recipients=user_id,
						subject="[ERPNext] [{frequency} Digest] {name}".format(
							frequency=self.frequency, name=self.name),
						msg=msg_for_this_receipient)

	def get_digest_msg(self):
		return self.get_msg_html(self.get_user_specific_content(frappe.session.user) + \
			self.get_common_content(), send_only_if_updates=False)

	def get_common_content(self):
		out = []
		for module, content in content_sequence:
			module_out = []
			for ctype in content:
				if self.get(ctype) and hasattr(self, "get_"+ctype):
					module_out.append(getattr(self, "get_"+ctype)())
			if any([m[0] for m in module_out]):
				out += [[1, "<h4>" + _(module) + "</h4>"]] + module_out + [[1, "<hr>"]]
			else:
				out += module_out

		return out

	def get_user_specific_content(self, user_id):
		original_session_user = frappe.session.user

		# setting session user for role base event fetching
		frappe.session.user = user_id

		out = []
		for ctype in user_specific_content:
			if self.get(ctype) and hasattr(self, "get_"+ctype):
				out.append(getattr(self, "get_"+ctype)(user_id))

		frappe.session.user = original_session_user

		return out

	def get_msg_html(self, out, send_only_if_updates=True):
		with_value = [o[1] for o in out if o[0]]

		if with_value:
			has_updates = True
			with_value = "\n".join(with_value)
		else:
			has_updates = False
			with_value = "<p>There were no updates in the items selected for this digest.</p><hr>"

		if not has_updates and send_only_if_updates:
			return

		# seperate out no value items
		no_value = [o[1] for o in out if not o[0]]
		if no_value:
			no_value = """<h4>No Updates For:</h4>""" + "\n".join(no_value)

		date = self.frequency == "Daily" and formatdate(self.from_date) or \
			"%s to %s" % (formatdate(self.from_date), formatdate(self.to_date))

		msg = digest_template % {
				"digest": self.frequency + " Digest",
				"date": date,
				"company": self.company,
				"with_value": with_value,
				"no_value": no_value or "",
				"name": self.name
			}

		return msg

	def get_income_year_to_date(self):
		return self.get_income(frappe.db.get_defaults("year_start_date"),
			self.meta.get_label("income_year_to_date"))

	def get_bank_balance(self):
		# account is of type "Bank" or "Cash"
		accounts = dict([[a["name"], [a["account_name"], 0]] for a in self.get_accounts()
			if a["account_type"] in ["Bank", "Cash"]])
		ackeys = accounts.keys()

		for gle in self.get_gl_entries(None, self.to_date):
			if gle["account"] in ackeys:
				accounts[gle["account"]][1] += gle["debit"] - gle["credit"]

		# build html
		out = self.get_html("Bank/Cash Balance as on " + formatdate(self.to_date), "", "")
		for ac in ackeys:
			if accounts[ac][1]:
				out += "\n" + self.get_html(accounts[ac][0], self.currency,
					fmt_money(accounts[ac][1]), style="margin-left: 17px")
		return sum((accounts[ac][1] for ac in ackeys)), out

	def get_income(self, from_date=None, label=None):
		accounts = [a["name"] for a in self.get_accounts() if a["root_type"]=="Income"]

		income = 0
		for gle in self.get_gl_entries(from_date or self.from_date, self.to_date):
			if gle["account"] in accounts:
				income += gle["credit"] - gle["debit"]

		return income, self.get_html(label or self.meta.get_label("income"), self.currency,
			fmt_money(income))

	def get_expenses_booked(self):
		accounts = [a["name"] for a in self.get_accounts() if a["root_type"]=="Expense"]

		expense = 0
		for gle in self.get_gl_entries(self.from_date, self.to_date):
			if gle["account"] in accounts:
				expense += gle["debit"] - gle["credit"]

		return expense, self.get_html(self.meta.get_label("expenses_booked"), self.currency,
			fmt_money(expense))

	def get_collections(self):
		return self.get_party_total("Customer", "credit", self.meta.get_label("collections"))

	def get_payments(self):
		return self.get_party_total("Supplier", "debit", self.meta.get_label("payments"))

	def get_party_total(self, party_type, gle_field, label):
		import re
		# account is of master_type Customer or Supplier
		accounts = [a["name"] for a in self.get_accounts()
			if a["master_type"]==party_type]

		# account is "Bank" or "Cash"
		bc_accounts = [esc(a["name"], "()|") for a in self.get_accounts()
			if a["account_type"] in ["Bank", "Cash"]]
		bc_regex = re.compile("""(%s)""" % "|".join(bc_accounts))

		total = 0
		for gle in self.get_gl_entries(self.from_date, self.to_date):
			# check that its made against a bank or cash account
			if gle["account"] in accounts and gle["against"] and \
					bc_regex.findall(gle["against"]):
				val = gle["debit"] - gle["credit"]
				total += (gle_field=="debit" and 1 or -1) * val

		return total, self.get_html(label, self.currency, fmt_money(total))

	def get_invoiced_amount(self):
		# aka receivables
		return self.get_booked_total("Customer", "debit", self.meta.get_label("invoiced_amount"))

	def get_payables(self):
		return self.get_booked_total("Supplier", "credit", self.meta.get_label("payables"))

	def get_booked_total(self, party_type, gle_field, label):
		# account is of master_type Customer or Supplier
		accounts = [a["name"] for a in self.get_accounts()
			if a["master_type"]==party_type]

		total = 0
		for gle in self.get_gl_entries(self.from_date, self.to_date):
			if gle["account"] in accounts:
				total += gle[gle_field]

		return total, self.get_html(label, self.currency, fmt_money(total))

	def get_new_leads(self):
		return self.get_new_count("Lead", self.meta.get_label("new_leads"))

	def get_new_enquiries(self):
		return self.get_new_count("Opportunity", self.meta.get_label("new_enquiries"), docstatus=1,
			date_field="transaction_date")

	def get_new_quotations(self):
		return self.get_new_sum("Quotation", self.meta.get_label("new_quotations"), "grand_total",
			date_field="transaction_date")

	def get_new_sales_orders(self):
		return self.get_new_sum("Sales Order", self.meta.get_label("new_sales_orders"), "grand_total",
			date_field="transaction_date")

	def get_new_delivery_notes(self):
		return self.get_new_sum("Delivery Note", self.meta.get_label("new_delivery_notes"), "grand_total",
			date_field="posting_date")

	def get_new_purchase_requests(self):
		return self.get_new_count("Material Request", self.meta.get_label("new_purchase_requests"), docstatus=1,
			date_field="transaction_date")

	def get_new_supplier_quotations(self):
		return self.get_new_sum("Supplier Quotation", self.meta.get_label("new_supplier_quotations"),
			"grand_total", date_field="transaction_date")

	def get_new_purchase_orders(self):
		return self.get_new_sum("Purchase Order", self.meta.get_label("new_purchase_orders"),
			"grand_total", date_field="transaction_date")

	def get_new_purchase_receipts(self):
		return self.get_new_sum("Purchase Receipt", self.meta.get_label("new_purchase_receipts"),
			"grand_total", date_field="posting_date")

	def get_new_stock_entries(self):
		return self.get_new_sum("Stock Entry", self.meta.get_label("new_stock_entries"), "total_amount",
			date_field="posting_date")

	def get_new_support_tickets(self):
		return self.get_new_count("Support Ticket", self.meta.get_label("new_support_tickets"),
			filter_by_company=False)

	def get_new_communications(self):
		return self.get_new_count("Communication", self.meta.get_label("new_communications"),
			filter_by_company=False)

	def get_new_projects(self):
		return self.get_new_count("Project", self.meta.get_label("new_projects"),
			filter_by_company=False)

	def get_calendar_events(self, user_id):
		from frappe.core.doctype.event.event import get_events
		events = get_events(self.future_from_date.strftime("%Y-%m-%d"), self.future_to_date.strftime("%Y-%m-%d"))

		html = ""
		if events:
			for i, e in enumerate(events):
				if i>=10:
					break
				if e.all_day:
					html += """<li style='line-height: 200%%'>%s [%s (%s)]</li>""" % \
						(e.subject, datetime_in_user_format(e.starts_on), _("All Day"))
				else:
					html += "<li style='line-height: 200%%'>%s [%s - %s]</li>" % \
						(e.subject, datetime_in_user_format(e.starts_on), datetime_in_user_format(e.ends_on))

		if html:
			return 1, "<h4>Upcoming Calendar Events (max 10):</h4><ul>" + html + "</ul><hr>"
		else:
			return 0, "<p>Calendar Events</p>"

	def get_todo_list(self, user_id):
		todo_list = frappe.db.sql("""select *
			from `tabToDo` where (owner=%s or assigned_by=%s) and status="Open"
			order by field(priority, 'High', 'Medium', 'Low') asc, date asc""",
			(user_id, user_id), as_dict=True)

		html = ""
		if todo_list:
			for i, todo in enumerate([todo for todo in todo_list if not todo.checked]):
				if i>= 10:
					break
				if not todo.description and todo.reference_type:
					todo.description = "%s: %s - %s %s" % \
					(todo.reference_type, get_url_to_form(todo.reference_type, todo.reference_name),
					_("assigned by"), get_fullname(todo.assigned_by))

				html += "<li style='line-height: 200%%'>%s [%s]</li>" % (todo.description, todo.priority)

		if html:
			return 1, "<h4>To Do (max 10):</h4><ul>" + html + "</ul><hr>"
		else:
			return 0, "<p>To Do</p>"

	def get_new_count(self, doctype, label, docstatus=0, filter_by_company=True, date_field="creation"):
		if filter_by_company:
			company_condition = """and company="%s" """ % self.company.replace('"', '\"')
		else:
			company_condition = ""

		count = frappe.db.sql("""select count(*) from `tab{doctype}`
			where ifnull(`docstatus`, 0)=%s {company_condition} and
			date(`{date_field}`)>=%s and date({date_field})<=%s""".format(doctype=doctype,
			company_condition=company_condition, date_field=date_field),
			(docstatus, self.from_date, self.to_date))

		count = count and count[0][0] or 0

		return count, self.get_html(label, None, count)

	def get_new_sum(self, doctype, label, sum_field, date_field="creation"):
		count_sum = frappe.db.sql("""select count(*), sum(ifnull(`{sum_field}`, 0))
			from `tab{doctype}` where docstatus=1 and company = %s and
			date(`{date_field}`)>=%s and date(`{date_field}`)<=%s""".format(sum_field=sum_field,
			date_field=date_field, doctype=doctype), (self.company, self.from_date, self.to_date))

		count, total = count_sum and count_sum[0] or (0, 0)

		return count, self.get_html(label, self.currency,
			"%s - (%s)" % (fmt_money(total), cstr(count)))

	def get_html(self, label, currency, value, style=None):
		"""get html output"""
		return row_template % {
				"style": style or "",
				"label": label,
				"currency": currency and (currency+" ") or "",
				"value": value
			}

	def get_gl_entries(self, from_date=None, to_date=None):
		"""get valid GL Entries filtered by company and posting date"""
		if from_date==self.from_date and to_date==self.to_date and \
				hasattr(self, "gl_entries"):
			return self.gl_entries

		gl_entries = frappe.db.sql("""select `account`,
			ifnull(credit, 0) as credit, ifnull(debit, 0) as debit, `against`
			from `tabGL Entry`
			where company=%s
			and posting_date <= %s %s""" % ("%s", "%s",
			from_date and "and posting_date>='%s'" % from_date or ""),
			(self.company, to_date or self.to_date), as_dict=1)

		# cache if it is the normal cases
		if from_date==self.from_date and to_date==self.to_date:
			self.gl_entries = gl_entries

		return gl_entries

	def get_accounts(self):
		if not hasattr(self, "accounts"):
			self.accounts = frappe.db.sql("""select name, account_type, account_name, master_type, root_type
				from `tabAccount` where company=%s and docstatus < 2
				and group_or_ledger = "Ledger" order by lft""",
				(self.company,), as_dict=1)
		return self.accounts

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

	def get_future_from_to_date(self):
		today = now_datetime().date()

		# decide from date based on email digest frequency
		if self.frequency == "Daily":
			# from date, to_date is today
			from_date = to_date = today
		elif self.frequency == "Weekly":
			# from date is the current week's monday
			from_date = today - timedelta(days=today.weekday())
			# to date is the current week's sunday
			to_date = from_date + timedelta(days=6)
		else:
			# from date is the 1st day of the current month
			from_date = today - relativedelta(days=today.day-1)
			# to date is the last day of the current month
			to_date = from_date + relativedelta(days=-1, months=1)

		return from_date, to_date

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

	def get_open_tickets(self):
		open_tickets = frappe.db.sql("""select name, subject, modified, raised_by
			from `tabSupport Ticket` where status='Open'
			order by modified desc limit 10""", as_dict=True)

		if open_tickets:
			return 1, """<hr><h4>Latest Open Tickets (max 10):</h4>%s""" % \
			 "".join(["<p>%(name)s: %(subject)s <br>by %(raised_by)s on %(modified)s</p>" % \
				t for t in open_tickets])
		else:
			return 0, "No Open Tickets!"

	def get_scheduler_errors(self):
		import frappe.utils.scheduler
		return frappe.utils.scheduler.get_error_report(self.from_date, self.to_date)

	def onload(self):
		self.get_next_sending()

def send():
	now_date = now_datetime().date()

	for ed in frappe.db.sql("""select name from `tabEmail Digest`
			where enabled=1 and docstatus<2""", as_list=1):
		ed_obj = frappe.get_doc('Email Digest', ed[0])
		if (now_date == ed_obj.get_next_sending()):
			ed_obj.send()
