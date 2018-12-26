# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe import utils
from frappe.model.document import Document
from frappe.utils import now, time_diff_in_hours, now_datetime, getdate
from datetime import datetime, timedelta
from frappe.utils.user import is_website_user

sender_field = "raised_by"

class Issue(Document):
	def get_feed(self):
		return "{0}: {1}".format(_(self.status), self.subject)

	def validate(self):
		if (self.get("__islocal") and self.via_customer_portal):
			self.flags.create_communication = True
		if not self.raised_by:
			self.raised_by = frappe.session.user
		self.update_status()
		self.set_lead_contact(self.raised_by)

		if self.status == "Closed":
			from frappe.desk.form.assign_to import clear
			clear(self.doctype, self.name)

	def on_update(self):
		# create the communication email and remove the description
		if (self.flags.create_communication and self.via_customer_portal):
			self.create_communication()
			self.flags.communication_created = None

	def set_lead_contact(self, email_id):
		import email.utils
		email_id = email.utils.parseaddr(email_id)[1]
		if email_id:
			if not self.lead:
				self.lead = frappe.db.get_value("Lead", {"email_id": email_id})
			if not self.contact and not self.customer:
				self.contact = frappe.db.get_value("Contact", {"email_id": email_id})

				if self.contact:
					contact = frappe.get_doc('Contact', self.contact)
					self.customer = contact.get_link_for('Customer')

			if not self.company:
				self.company = frappe.db.get_value("Lead", self.lead, "company") or \
					frappe.db.get_default("Company")

	def update_status(self):
		status = frappe.db.get_value("Issue", self.name, "status")
		if self.status!="Open" and status =="Open" and not self.first_responded_on:
			self.first_responded_on = now()
		if self.status=="Closed" and status !="Closed":
			self.resolution_date = now()
		if self.status=="Open" and status !="Open":
			# if no date, it should be set as None and not a blank string "", as per mysql strict config
			self.resolution_date = None

	def create_communication(self):
		communication = frappe.new_doc("Communication")
		communication.update({
			"communication_type": "Communication",
			"communication_medium": "Email",
			"sent_or_received": "Received",
			"email_status": "Open",
			"subject": self.subject,
			"sender": self.raised_by,
			"content": self.description,
			"status": "Linked",
			"reference_doctype": "Issue",
			"reference_name": self.name
		})
		communication.ignore_permissions = True
		communication.ignore_mandatory = True
		communication.save()

		self.db_set("description", "")

	def split_issue(self, subject, communication_id):
		# Bug: Pressing enter doesn't send subject
		from copy import deepcopy
		replicated_issue = deepcopy(self)
		replicated_issue.subject = subject
		frappe.get_doc(replicated_issue).insert()
		# Replicate linked Communications
		# todo get all communications in timeline before this, and modify them to append them to new doc
		comm_to_split_from = frappe.get_doc("Communication", communication_id)
		communications = frappe.get_all("Communication", filters={"reference_name": comm_to_split_from.reference_name, "reference_doctype": "Issue", "creation": ('>=', comm_to_split_from.creation)})
		for communication in communications:
			doc = frappe.get_doc("Communication", communication.name)
			doc.reference_name = replicated_issue.name
			doc.save(ignore_permissions=True)
		return replicated_issue.name

	def before_insert(self):
		week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday','Friday', 'Saturday', 'Sunday']
		support_contract = frappe.get_list("Support Contract", filters=[{"customer": self.customer, "contract_status": "Active"}], fields=["name", "service_level", "holiday_list", "priority"], limit=1)
		if not support_contract:
			support_contract = frappe.get_list("Support Contract", filters=[{"default_contract": "1"}], fields=["name", "service_level", "holiday_list", "priority"], limit=1)
		if support_contract:
			self.support_contract = support_contract[0].name
			self.priority = support_contract[0].priority
			service_level = frappe.get_doc("Service Level", support_contract[0].service_level)
			support_days = [[service.workday, str(service.start_time), str(service.end_time)] for service in service_level.support_and_resolution]
			holiday_list = frappe.get_doc("Holiday List", support_contract[0].holiday_list)
			holidays = [holiday.holiday_date for holiday in holiday_list.holidays]
			time, add_days, now_datetime = 0, 0, utils.now_datetime()
			while time != 1:
				for count, weekday in enumerate(week):
					if count >= (getdate()).weekday() or add_days != 0:
						if time != 1:
							for service in service_level.support_and_resolution:
								if service.workday == weekday:
									now_datetime += timedelta(days=add_days)
									self.response_by, self.time_to_respond = self.calculate_support_day(now_datetime=now_datetime, time=int(service_level.response_time), time_period=service_level.response_time_period, support_days=support_days, holidays=holidays, week=week)
									self.resolution_by, self.time_to_resolve = self.calculate_support_day(now_datetime=now_datetime, time=int(service_level.resolution_time), time_period=service_level.resolution_time_period, support_days=support_days, holidays=holidays, week=week)
									time = 1
							add_days += 1

	def calculate_support_day(self, now_datetime=None, time=None, time_period=None, support_days=None, holidays=None, week=None):
		now_datetime, add_days, hours, end_time = now_datetime, 0, 0, None
		#	Time is primarily calculated in days so if time_period is Days then loop is iterated, if time_period is Weeks then time is multiplied by 7 to convert
		#	it to days and if time_period is Hours then time is passed to calculate time to calculate_support_time function
		if time_period == 'Hour/s':
			time, hours = 0, time
		elif time_period == 'Week/s':
			time *= 7
		while time != 0:
			for count, weekday in enumerate(week):
				#	To search the week from the current weekday
				if count >= (now_datetime.date()).weekday() or add_days != 0:
					if time != 0:
						for support_day in support_days:
							if weekday == support_day[0]:
								time -= 1
								if not hours:
									end_time = datetime.strptime(support_day[2], '%H:%M:%S').time()
						add_days += 1
		now_datetime += timedelta(days=add_days)
		if not hours:
			support = datetime.combine(now_datetime.date(), end_time)
		else:
			support = calculate_support_time(time=now_datetime, hours=hours, support_days=support_days, holidays=holidays, week=week)
		return support, round(time_diff_in_hours(support, utils.now_datetime()), 2)

def calculate_support_time(time=None, hours=None, support_days=None, holidays=None, week=None):
	time_difference, time_added_flag, time_set_flag = 0, 0, 0
	# Loop starts counting from current weekday and iterates till time_set_flag is set indicating the time has been calculated.
	while time_set_flag != 1:
		for count, weekday in enumerate(week):
			# Initially time_added_flag is zero and the code will only start executing if today and weekday is the same and keep executing
			# henceforth as time_add is incremented.
			if count >= (time.date()).weekday() or time_added_flag != 0:
				for support_day in support_days:
					if weekday == support_day[0] and time_set_flag != 1:
						start_time, end_time = datetime.strptime(support_day[1], '%H:%M:%S').time(), datetime.strptime(support_day[2], '%H:%M:%S').time()
						# If the time is between start and end time then hours is added and then conditions are checked to avoid addition of extra day
						if time.time() <= end_time and time.time() >= start_time and hours and time_added_flag == 0:
							time += timedelta(hours=hours)
							time_added_flag = 1
						if time_difference:
							time = datetime.combine(time.date(), start_time)
							time += timedelta(seconds=time_difference)
						if time.time() <= start_time:
							if time_added_flag == 1:
								# If first day of the week then previous day is the last item of the list
								if support_days.index(support_day) == 0:
									prev_day_end_time = support_days[len(support_days)-1][2]
								else:
									prev_day_end_time = support_days[support_days.index(support_day)][2]
								time_difference = (time - datetime.combine(time.date()-timedelta(days=1), datetime.strptime(prev_day_end_time, '%H:%M:%S').time())).total_seconds()
								time -= timedelta(days=1)	# Time is reduced by one day as one day is calculated extra
							else:
								time = datetime.combine(time.date(), start_time)
								time += timedelta(hours=hours)
								time_added_flag = 1
						elif time.time() <= end_time and time.time() >= start_time:
							time_set_flag = 1
							break
						elif time.time() >= end_time:
							if time_added_flag == 1:
								time_difference = (time - datetime.combine(time.date(), end_time)).total_seconds()
							else:
								time_difference = hours * 3600
								time_added_flag = 1
						#	Checks if date is present in the holiday list
						if time.date() in holidays:
							continue
						# Time is checked after every calculation whether time is between start and end time for the day to be sure if
						# calculated time is between start and end time fo the particular day
						if time.time() <= end_time and time.time() >= start_time:
							time_set_flag = 1
							break
				if time_set_flag != 1:
					time += timedelta(days=1)
	return time

def get_list_context(context=None):
	return {
		"title": _("Issues"),
		"get_list": get_issue_list,
		"row_template": "templates/includes/issue_row.html",
		"show_sidebar": True,
		"show_search": True,
		'no_breadcrumbs': True
	}

def get_issue_list(doctype, txt, filters, limit_start, limit_page_length=20, order_by=None):
	from frappe.www.list import get_list
	user = frappe.session.user
	contact = frappe.db.get_value('Contact', {'user': user}, 'name')
	customer = None
	if contact:
		contact_doc = frappe.get_doc('Contact', contact)
		customer = contact_doc.get_link_for('Customer')

	ignore_permissions = False
	if is_website_user():
		if not filters: filters = []
		filters.append(("Issue", "customer", "=", customer)) if customer else filters.append(("Issue", "raised_by", "=", user))
		ignore_permissions = True

	return get_list(doctype, txt, filters, limit_start, limit_page_length, ignore_permissions=ignore_permissions)

@frappe.whitelist()
def set_status(name, status):
	st = frappe.get_doc("Issue", name)
	st.status = status
	st.save()

def auto_close_tickets():
	""" auto close the replied support tickets after 7 days """
	auto_close_after_days = frappe.db.get_value("Support Settings", "Support Settings", "close_issue_after_days") or 7

	issues = frappe.db.sql(""" select name from tabIssue where status='Replied' and
		modified<DATE_SUB(CURDATE(), INTERVAL %s DAY) """, (auto_close_after_days), as_dict=True)

	for issue in issues:
		doc = frappe.get_doc("Issue", issue.get("name"))
		doc.status = "Closed"
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
		doc.save()

@frappe.whitelist()
def set_multiple_status(names, status):
	names = json.loads(names)
	for name in names:
		set_status(name, status)
def has_website_permission(doc, ptype, user, verbose=False):
	from erpnext.controllers.website_list_for_contact import has_website_permission
	permission_based_on_customer = has_website_permission(doc, ptype, user, verbose)

	return permission_based_on_customer or doc.raised_by==user

def update_issue(contact, method):
	"""Called when Contact is deleted"""
	frappe.db.sql("""UPDATE `tabIssue` set contact='' where contact=%s""", contact.name)

def update_support_timer():
	issues = frappe.get_list("Issue", filters={"service_contract_status": "Ongoing", "status": "Open"})
	issues.reverse()
	for issue in issues:
		issue = frappe.get_doc("Issue", issue.name)
		if float(issue.time_to_respond) > 0 and not issue.first_responded_on:
			issue.time_to_respond = round(time_diff_in_hours(issue.response_by, now_datetime()), 2)
		if float(issue.time_to_resolve) > 0:
			issue.time_to_resolve = round(time_diff_in_hours(issue.resolution_by, now_datetime()), 2)
		if float(issue.time_to_respond) < 0 or float(issue.time_to_resolve) < 0:
			issue.service_contract_status = "Failed"
		else:
			issue.service_contract_status = "Fulfilled"
		issue.save()