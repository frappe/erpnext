# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes import _
from webnotes.utils import fmt_money, formatdate, now_datetime, cstr, esc, get_url_to_form
from webnotes.utils.dateutils import datetime_in_user_format
from datetime import timedelta
from dateutil.relativedelta import relativedelta

content_sequence = [
	["Accounts", ["income_year_to_date", "bank_balance",
		"income", "expenses_booked", "collections", "payments",
		"invoiced_amount", "payables"]],
	["Buying", ["new_purchase_requests", "new_supplier_quotations", "new_purchase_orders"]],
	["Selling", ["new_leads", "new_enquiries", "new_quotations", "new_sales_orders"]], 
	["Stock", ["new_delivery_notes",  "new_purchase_receipts", "new_stock_entries"]], 
	["Support", ["new_communications", "new_support_tickets", "open_tickets"]], 
	["Projects", ["new_projects"]]
]

user_specific_content = ["calendar_events", "todo_list"]

digest_template = 	"""\
<style>p.ed-indent { margin-right: 17px; }</style>
<h2>%(digest)s</h2>
<p style='color: grey'>%(date)s</p>
<h4>%(company)s</h4>
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

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc, self.doclist = doc, doclist
		self.from_date, self.to_date = self.get_from_to_date()
		self.future_from_date, self.future_to_date = self.get_future_from_to_date()
		self.currency = webnotes.conn.get_value("Company", self.doc.company,
			"default_currency")

	def get_profiles(self):
		"""get list of profiles"""
		import webnotes
		profile_list = webnotes.conn.sql("""
			select name, enabled from tabProfile
			where docstatus=0 and name not in ('Administrator', 'Guest')
			order by enabled desc, name asc""", as_dict=1)

		if self.doc.recipient_list:
			recipient_list = self.doc.recipient_list.split("\n")
		else:
			recipient_list = []
		for p in profile_list:
			p["checked"] = p["name"] in recipient_list and 1 or 0

		webnotes.response['profile_list'] = profile_list
	
	def send(self):
		# send email only to enabled users
		valid_users = [p[0] for p in webnotes.conn.sql("""select name from `tabProfile`
			where enabled=1""")]
		recipients = filter(lambda r: r in valid_users,
			self.doc.recipient_list.split("\n"))
		
		common_msg = self.get_common_content()
		if recipients:
			for user_id in recipients:
				msg_for_this_receipient = self.get_msg_html(self.get_user_specific_content(user_id) + \
					common_msg)
				from webnotes.utils.email_lib import sendmail
				sendmail(recipients=user_id, subject=(self.doc.frequency + " Digest"),
					sender="ERPNext Notifications <notifications+email_digest@erpnext.com>",
					msg=msg_for_this_receipient)
			
	def get_digest_msg(self):
		return self.get_msg_html(self.get_user_specific_content(webnotes.session.user) + \
			self.get_common_content())
	
	def get_common_content(self):
		out = []
		for module, content in content_sequence:
			module_out = []
			for ctype in content:
				if self.doc.fields.get(ctype) and hasattr(self, "get_"+ctype):
					module_out.append(getattr(self, "get_"+ctype)())
			if any([m[0] for m in module_out]):
				out += [[1, "<h4>" + _(module) + "</h4>"]] + module_out + [[1, "<hr>"]]
			else:
				out += module_out
				
		return out
		
	def get_user_specific_content(self, user_id):
		original_session_user = webnotes.session.user
		
		# setting session user for role base event fetching
		webnotes.session.user = user_id
		
		out = []
		for ctype in user_specific_content:
			if self.doc.fields.get(ctype) and hasattr(self, "get_"+ctype):
				out.append(getattr(self, "get_"+ctype)(user_id))
				
		webnotes.session.user = original_session_user
		
		return out
				
	def get_msg_html(self, out):
		with_value = [o[1] for o in out if o[0]]
		
		if with_value:
			with_value = "\n".join(with_value)
		else:
			with_value = "<p>There were no updates in the items selected for this digest.</p>"
		
		# seperate out no value items
		no_value = [o[1] for o in out if not o[0]]
		if no_value:
			no_value = """<h4>No Updates For:</h4>""" + "\n".join(no_value)
		
		date = self.doc.frequency == "Daily" and formatdate(self.from_date) or \
			"%s to %s" % (formatdate(self.from_date), formatdate(self.to_date))
		
		msg = digest_template % {
				"digest": self.doc.frequency + " Digest",
				"date": date,
				"company": self.doc.company,
				"with_value": with_value,
				"no_value": no_value or ""
			}
		
		return msg
	
	def get_income_year_to_date(self):
		return self.get_income(webnotes.conn.get_defaults("year_start_date"), 
			"Income Year To Date")
			
	def get_bank_balance(self):
		# account is of type "Bank or Cash"
		accounts = dict([[a["name"], [a["account_name"], 0]] for a in self.get_accounts()
			if a["account_type"]=="Bank or Cash"])
		ackeys = accounts.keys()
		
		for gle in self.get_gl_entries(None, self.to_date):
			if gle["account"] in ackeys:
				accounts[gle["account"]][1] += gle["debit"] - gle["credit"]
		
		# build html
		out = self.get_html("Bank/Cash Balance", "", "")
		for ac in ackeys:
			if accounts[ac][1]:
				out += "\n" + self.get_html(accounts[ac][0], self.currency,
					fmt_money(accounts[ac][1]), style="margin-left: 17px")
		return sum((accounts[ac][1] for ac in ackeys)), out
		
	def get_income(self, from_date=None, label=None):
		# account is PL Account and Credit type account
		accounts = [a["name"] for a in self.get_accounts()
			if a["is_pl_account"]=="Yes" and a["debit_or_credit"]=="Credit"]
			
		income = 0
		for gle in self.get_gl_entries(from_date or self.from_date, self.to_date):
			if gle["account"] in accounts:
				income += gle["credit"] - gle["debit"]
		
		return income, self.get_html(label or "Income", self.currency, fmt_money(income))
		
	def get_expenses_booked(self):
		# account is PL Account and Debit type account
		accounts = [a["name"] for a in self.get_accounts()
			if a["is_pl_account"]=="Yes" and a["debit_or_credit"]=="Debit"]
			
		expense = 0
		for gle in self.get_gl_entries(self.from_date, self.to_date):
			if gle["account"] in accounts:
				expense += gle["debit"] - gle["credit"]
		
		return expense, self.get_html("Expenses", self.currency, fmt_money(expense))
	
	def get_collections(self):
		return self.get_party_total("Customer", "credit", "Collections")
	
	def get_payments(self):
		return self.get_party_total("Supplier", "debit", "Payments")
		
	def get_party_total(self, party_type, gle_field, label):
		import re
		# account is of master_type Customer or Supplier
		accounts = [a["name"] for a in self.get_accounts()
			if a["master_type"]==party_type]

		# account is "Bank or Cash"
		bc_accounts = [esc(a["name"], "()|") for a in self.get_accounts() 
			if a["account_type"]=="Bank or Cash"]
		bc_regex = re.compile("""(%s)""" % "|".join(bc_accounts))
		
		total = 0
		for gle in self.get_gl_entries(self.from_date, self.to_date):
			# check that its made against a bank or cash account
			if gle["account"] in accounts and gle["against"] and \
					bc_regex.findall(gle["against"]):
				total += gle[gle_field]

		return total, self.get_html(label, self.currency, fmt_money(total))
		
	def get_invoiced_amount(self):
		# aka receivables
		return self.get_booked_total("Customer", "debit", "Receivables")

	def get_payables(self):
		return self.get_booked_total("Supplier", "credit", "Payables")
		
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
		return self.get_new_count("Lead", "New Leads")
		
	def get_new_enquiries(self):
		return self.get_new_count("Opportunity", "New Opportunities")
	
	def get_new_quotations(self):
		return self.get_new_sum("Quotation", "New Quotations", "grand_total")
		
	def get_new_sales_orders(self):
		return self.get_new_sum("Sales Order", "New Sales Orders", "grand_total")
		
	def get_new_delivery_notes(self):
		return self.get_new_sum("Delivery Note", "New Delivery Notes", "grand_total")
		
	def get_new_purchase_requests(self):
		return self.get_new_count("Purchase Request", "New Purchase Requests")
		
	def get_new_supplier_quotations(self):
		return self.get_new_sum("Supplier Quotation", "New Supplier Quotations",
			"grand_total")
	
	def get_new_purchase_orders(self):
		return self.get_new_sum("Purchase Order", "New Purchase Orders", "grand_total")
	
	def get_new_purchase_receipts(self):
		return self.get_new_sum("Purchase Receipt", "New Purchase Receipts",
			"grand_total")
	
	def get_new_stock_entries(self):
		return self.get_new_sum("Stock Entry", "New Stock Entries", "total_amount")
		
	def get_new_support_tickets(self):
		return self.get_new_count("Support Ticket", "New Support Tickets", False)
		
	def get_new_communications(self):
		return self.get_new_count("Communication", "New Communications", False)
		
	def get_new_projects(self):
		return self.get_new_count("Project", "New Projects", False)
		
	def get_calendar_events(self, user_id):
		from core.doctype.event.event import get_events
		events = get_events(self.future_from_date, self.future_to_date)
		
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
		
		return html and 1 or 0, "<h4>Upcoming Calendar Events (max 10):</h4><ul>" + html + "</ul><hr>"
	
	def get_todo_list(self, user_id):
		from utilities.page.todo.todo import get
		todo_list = get()
		
		html = ""
		if todo_list:
			for i, todo in enumerate([todo for todo in todo_list if not todo.checked]):
				if i>= 10:
					break
				html += "<li style='line-height: 200%%'>%s [%s]</li>" % (todo.description or \
					get_url_to_form(todo.reference_type, todo.reference_name), todo.priority)
				
			
		return html and 1 or 0, "<h4>To Do (max 10):</h4><ul>" + html + "</ul><hr>"
	
	def get_new_count(self, doctype, label, filter_by_company=True):
		if filter_by_company:
			company = """and company="%s" """ % self.doc.company
		else:
			company = ""
		count = webnotes.conn.sql("""select count(*) from `tab%s`
			where docstatus < 2 %s and
			date(creation)>=%s and date(creation)<=%s""" % (doctype, company, "%s", "%s"),
			(self.from_date, self.to_date))
		count = count and count[0][0] or 0
		
		return count, self.get_html(label, None, count)
		
	def get_new_sum(self, doctype, label, sum_field):
		count_sum = webnotes.conn.sql("""select count(*), sum(ifnull(`%s`, 0))
			from `tab%s` where docstatus < 2 and company = %s and
			date(creation)>=%s and date(creation)<=%s""" % (sum_field, doctype, "%s",
			"%s", "%s"), (self.doc.company, self.from_date, self.to_date))
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
		
		gl_entries = webnotes.conn.sql("""select `account`, 
			ifnull(credit, 0) as credit, ifnull(debit, 0) as debit, `against`
			from `tabGL Entry`
			where company=%s and ifnull(is_cancelled, "No")="No" and
			posting_date <= %s %s""" % ("%s", "%s", 
			from_date and "and posting_date>='%s'" % from_date or ""),
			(self.doc.company, to_date or self.to_date), as_dict=1)
		
		# cache if it is the normal cases
		if from_date==self.from_date and to_date==self.to_date:
			self.gl_entries = gl_entries
		
		return gl_entries
		
	def get_accounts(self):
		if not hasattr(self, "accounts"):
			self.accounts = webnotes.conn.sql("""select name, is_pl_account,
				debit_or_credit, account_type, account_name, master_type
				from `tabAccount` where company=%s and docstatus < 2
				order by lft""",
				(self.doc.company,), as_dict=1)
		return self.accounts
		
	def get_from_to_date(self):
		today = now_datetime().date()
		
		# decide from date based on email digest frequency
		if self.doc.frequency == "Daily":
			# from date, to_date is yesterday
			from_date = to_date = today - timedelta(days=1)
		elif self.doc.frequency == "Weekly":
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
		if self.doc.frequency == "Daily":
			# from date, to_date is today
			from_date = to_date = today
		elif self.doc.frequency == "Weekly":
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
		
		if self.doc.frequency == "Daily":
			next_send_date = send_date + timedelta(days=1)
		elif self.doc.frequency == "Weekly":
			next_send_date = send_date + timedelta(weeks=1)
		else:
			next_send_date = send_date + relativedelta(months=1)
		self.doc.next_send = formatdate(next_send_date) + " at midnight"
		
		return send_date
	
	def get_open_tickets(self):
		open_tickets = webnotes.conn.sql("""select name, subject, modified, raised_by
			from `tabSupport Ticket` where status='Open'
			order by modified desc limit 10""", as_dict=True)
			
		if open_tickets:
			return 1, """<hr><h4>Latest Open Tickets (max 10):</h4>%s""" % \
			 "".join(["<p>%(name)s: %(subject)s <br>by %(raised_by)s on %(modified)s</p>" % \
				t for t in open_tickets])
		else:
			return 0, "No Open Tickets!"
	
	def onload(self):
		self.get_next_sending()

def send():
	from webnotes.model.code import get_obj
	from webnotes.utils import getdate
	now_date = now_datetime().date()
	
	import conf
	if hasattr(conf, "expires_on") and now_date > getdate(conf.expires_on):
		# do not send email digests to expired accounts
		return
	
	for ed in webnotes.conn.sql("""select name from `tabEmail Digest`
			where enabled=1 and docstatus<2""", as_list=1):
		ed_obj = get_obj('Email Digest', ed[0])
		if (now_date == ed_obj.get_next_sending()):
			ed_obj.send()
