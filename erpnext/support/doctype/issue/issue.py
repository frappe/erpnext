# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe import utils
from frappe.model.document import Document
from frappe.utils import now, time_diff_in_hours, now_datetime, getdate, get_weekdays, add_to_date, today, get_time, get_datetime
from datetime import datetime, timedelta
from frappe.model.mapper import get_mapped_doc
from frappe.utils.user import is_website_user
from erpnext.support.doctype.service_level_agreement.service_level_agreement import get_active_service_level_agreement_for
from frappe.email.inbox import link_communication_to_document

sender_field = "raised_by"


class Issue(Document):
	def get_feed(self):
		return "{0}: {1}".format(_(self.status), self.subject)

	def validate(self):
		if self.is_new() and self.via_customer_portal:
			self.flags.create_communication = True

		if not self.raised_by:
			self.raised_by = frappe.session.user

		self.change_service_level_agreement_and_priority()
		self.update_status()
		self.set_lead_contact(self.raised_by)

	def on_update(self):
		# Add a communication in the issue timeline
		if self.flags.create_communication and self.via_customer_portal:
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
			self.first_responded_on = frappe.flags.current_time or now_datetime()

		if self.status=="Closed" and status !="Closed":
			self.resolution_date = frappe.flags.current_time or now_datetime()
			if frappe.db.get_value("Issue", self.name, "agreement_fulfilled") == "Ongoing":
				set_service_level_agreement_variance(issue=self.name)
				self.update_agreement_status()

		if self.status=="Open" and status !="Open":
			# if no date, it should be set as None and not a blank string "", as per mysql strict config
			self.resolution_date = None

	def update_agreement_status(self):
		if self.service_level_agreement and self.agreement_fulfilled == "Ongoing":
			if frappe.db.get_value("Issue", self.name, "response_by_variance") < 0 or \
				frappe.db.get_value("Issue", self.name, "resolution_by_variance") < 0:

				self.agreement_fulfilled = "Failed"
			else:
				self.agreement_fulfilled = "Fulfilled"

	def update_agreement_fulfilled_on_custom_status(self):
		"""
			Update Agreement Fulfilled status using Custom Scripts for Custom Issue Status
		"""
		if not self.first_responded_on: # first_responded_on set when first reply is sent to customer
			self.response_by_variance = round(time_diff_in_hours(self.response_by, now_datetime()), 2)

		if not self.resolution_date: # resolution_date set when issue has been closed
			self.resolution_by_variance = round(time_diff_in_hours(self.resolution_by, now_datetime()), 2)

		self.agreement_fulfilled = "Fulfilled" if self.response_by_variance > 0 and self.resolution_by_variance > 0 else "Failed"

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

	def split_issue(self, subject, communication_id):
		# Bug: Pressing enter doesn't send subject
		from copy import deepcopy

		replicated_issue = deepcopy(self)
		replicated_issue.subject = subject
		replicated_issue.issue_split_from = self.name
		replicated_issue.mins_to_first_response = 0
		replicated_issue.first_responded_on = None
		replicated_issue.creation = now_datetime()

		# Reset SLA
		if replicated_issue.service_level_agreement:
			replicated_issue.service_level_agreement_creation = now_datetime()
			replicated_issue.service_level_agreement = None
			replicated_issue.agreement_fulfilled = "Ongoing"
			replicated_issue.response_by = None
			replicated_issue.response_by_variance = None
			replicated_issue.resolution_by = None
			replicated_issue.resolution_by_variance = None

		frappe.get_doc(replicated_issue).insert()

		# Replicate linked Communications
		# TODO: get all communications in timeline before this, and modify them to append them to new doc
		comm_to_split_from = frappe.get_doc("Communication", communication_id)
		communications = frappe.get_all("Communication",
			filters={"reference_doctype": "Issue",
				"reference_name": comm_to_split_from.reference_name,
				"creation": ('>=', comm_to_split_from.creation)})

		for communication in communications:
			doc = frappe.get_doc("Communication", communication.name)
			doc.reference_name = replicated_issue.name
			doc.save(ignore_permissions=True)

		frappe.get_doc({
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": "Issue",
			"reference_name": replicated_issue.name,
			"content": " - Split the Issue from <a href='#Form/Issue/{0}'>{1}</a>".format(self.name, frappe.bold(self.name)),
		}).insert(ignore_permissions=True)

		return replicated_issue.name

	def before_insert(self):
		if frappe.db.get_single_value("Support Settings", "track_service_level_agreement"):
			self.set_response_and_resolution_time()

	def set_response_and_resolution_time(self, priority=None, service_level_agreement=None):
		service_level_agreement = get_active_service_level_agreement_for(priority=priority,
			customer=self.customer, service_level_agreement=service_level_agreement)

		if not service_level_agreement:
			if frappe.db.get_value("Issue", self.name, "service_level_agreement"):
				frappe.throw(_("Couldn't Set Service Level Agreement {0}.".format(self.service_level_agreement)))
			return

		if (service_level_agreement.customer and self.customer) and not (service_level_agreement.customer == self.customer):
			frappe.throw(_("This Service Level Agreement is specific to Customer {0}".format(service_level_agreement.customer)))

		self.service_level_agreement = service_level_agreement.name
		self.priority = service_level_agreement.default_priority if not priority else priority

		service_level_agreement = frappe.get_doc("Service Level Agreement", service_level_agreement.name)
		priority = service_level_agreement.get_service_level_agreement_priority(self.priority)
		priority.update({
			"support_and_resolution": service_level_agreement.support_and_resolution,
			"holiday_list": service_level_agreement.holiday_list
		})

		if not self.creation:
			self.creation = now_datetime()
			self.service_level_agreement_creation = now_datetime()

		start_date_time = get_datetime(self.service_level_agreement_creation)
		self.response_by = get_expected_time_for(parameter='response', service_level=priority, start_date_time=start_date_time)
		self.resolution_by = get_expected_time_for(parameter='resolution', service_level=priority, start_date_time=start_date_time)

		self.response_by_variance = round(time_diff_in_hours(self.response_by, now_datetime()))
		self.resolution_by_variance = round(time_diff_in_hours(self.resolution_by, now_datetime()))

	def change_service_level_agreement_and_priority(self):
		if self.service_level_agreement and frappe.db.exists("Issue", self.name) and \
			frappe.db.get_single_value("Support Settings", "track_service_level_agreement"):

			if not self.priority == frappe.db.get_value("Issue", self.name, "priority"):
				self.set_response_and_resolution_time(priority=self.priority, service_level_agreement=self.service_level_agreement)
				frappe.msgprint(_("Priority has been changed to {0}.").format(self.priority))

			if not self.service_level_agreement == frappe.db.get_value("Issue", self.name, "service_level_agreement"):
				self.set_response_and_resolution_time(priority=self.priority, service_level_agreement=self.service_level_agreement)
				frappe.msgprint(_("Service Level Agreement has been changed to {0}.").format(self.service_level_agreement))

	def reset_service_level_agreement(self, reason, user):
		if not frappe.db.get_single_value("Support Settings", "allow_resetting_service_level_agreement"):
			frappe.throw(_("Allow Resetting Service Level Agreement from Support Settings."))

		frappe.get_doc({
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": self.doctype,
			"reference_name": self.name,
			"comment_email": user,
			"content": " resetted Service Level Agreement - {0}".format(_(reason)),
		}).insert(ignore_permissions=True)

		self.service_level_agreement_creation = now_datetime()
		self.set_response_and_resolution_time(priority=self.priority, service_level_agreement=self.service_level_agreement)
		self.agreement_fulfilled = "Ongoing"
		self.save()

def get_expected_time_for(parameter, service_level, start_date_time):
	current_date_time = start_date_time
	expected_time = current_date_time
	start_time = None
	end_time = None

	# lets assume response time is in days by default
	if parameter == 'response':
		allotted_days = service_level.get("response_time")
		time_period = service_level.get("response_time_period")
	elif parameter == 'resolution':
		allotted_days = service_level.get("resolution_time")
		time_period = service_level.get("resolution_time_period")
	else:
		frappe.throw(_("{0} parameter is invalid".format(parameter)))

	allotted_hours = 0
	if time_period == 'Hour':
		allotted_hours = allotted_days
		allotted_days = 0
	elif time_period == 'Week':
		allotted_days *= 7

	expected_time_is_set = 1 if allotted_days == 0 and time_period in ['Day', 'Week'] else 0

	support_days = {}
	for service in service_level.get("support_and_resolution"):
		support_days[service.workday] = frappe._dict({
			'start_time': service.start_time,
			'end_time': service.end_time,
		})

	holidays = get_holidays(service_level.get("holiday_list"))
	weekdays = get_weekdays()

	while not expected_time_is_set:
		current_weekday = weekdays[current_date_time.weekday()]

		if not is_holiday(current_date_time, holidays) and current_weekday in support_days:
			start_time = current_date_time - datetime(current_date_time.year, current_date_time.month, current_date_time.day) \
				if getdate(current_date_time) == getdate(start_date_time) and get_time_in_timedelta(current_date_time.time()) > support_days[current_weekday].start_time \
				else support_days[current_weekday].start_time
			end_time = support_days[current_weekday].end_time
			time_left_today = time_diff_in_hours(end_time, start_time)

			# no time left for support today
			if time_left_today < 0: pass
			elif time_period == 'Hour':
				if time_left_today >= allotted_hours:
					expected_time = datetime.combine(getdate(current_date_time), get_time(start_time))
					expected_time = add_to_date(expected_time, hours=allotted_hours)
					expected_time_is_set = 1
				else:
					allotted_hours = allotted_hours - time_left_today
			else:
				allotted_days -= 1
				expected_time_is_set = allotted_days <= 0

		if not expected_time_is_set:
			current_date_time = add_to_date(current_date_time, days=1)

	if end_time and time_period != 'Hour':
		current_date_time = datetime.combine(getdate(current_date_time), get_time(end_time))
	else:
		current_date_time = expected_time

	return current_date_time

def set_service_level_agreement_variance(issue=None):
	current_time = frappe.flags.current_time or now_datetime()

	filters = {"status": "Open", "agreement_fulfilled": "Ongoing"}
	if issue:
		filters = {"name": issue}

	for issue in frappe.get_list("Issue", filters=filters):
		doc = frappe.get_doc("Issue", issue.name)

		if not doc.first_responded_on: # first_responded_on set when first reply is sent to customer
			variance = round(time_diff_in_hours(doc.response_by, current_time), 2)
			frappe.db.set_value(dt="Issue", dn=doc.name, field="response_by_variance", val=variance, update_modified=False)
			if variance < 0:
				frappe.db.set_value(dt="Issue", dn=doc.name, field="agreement_fulfilled", val="Failed", update_modified=False)

		if not doc.resolution_date: # resolution_date set when issue has been closed
			variance = round(time_diff_in_hours(doc.resolution_by, current_time), 2)
			frappe.db.set_value(dt="Issue", dn=doc.name, field="resolution_by_variance", val=variance, update_modified=False)
			if variance < 0:
				frappe.db.set_value(dt="Issue", dn=doc.name, field="agreement_fulfilled", val="Failed", update_modified=False)

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
		if not filters: filters = {}

		if customer:
			filters["customer"] = customer
		else:
			filters["raised_by"] = user

		ignore_permissions = True

	return get_list(doctype, txt, filters, limit_start, limit_page_length, ignore_permissions=ignore_permissions)


@frappe.whitelist()
def set_multiple_status(names, status):
	names = json.loads(names)
	for name in names:
		set_status(name, status)

@frappe.whitelist()
def set_status(name, status):
	st = frappe.get_doc("Issue", name)
	st.status = status
	st.save()

def auto_close_tickets():
	"""Auto-close replied support tickets after 7 days"""
	auto_close_after_days = frappe.db.get_value("Support Settings", "Support Settings", "close_issue_after_days") or 7

	issues = frappe.db.sql(""" select name from tabIssue where status='Replied' and
		modified<DATE_SUB(CURDATE(), INTERVAL %s DAY) """, (auto_close_after_days), as_dict=True)

	for issue in issues:
		doc = frappe.get_doc("Issue", issue.get("name"))
		doc.status = "Closed"
		doc.flags.ignore_permissions = True
		doc.flags.ignore_mandatory = True
		doc.save()

def has_website_permission(doc, ptype, user, verbose=False):
	from erpnext.controllers.website_list_for_contact import has_website_permission
	permission_based_on_customer = has_website_permission(doc, ptype, user, verbose)

	return permission_based_on_customer or doc.raised_by==user

def update_issue(contact, method):
	"""Called when Contact is deleted"""
	frappe.db.sql("""UPDATE `tabIssue` set contact='' where contact=%s""", contact.name)

def get_holidays(holiday_list_name):
	holiday_list = frappe.get_cached_doc("Holiday List", holiday_list_name)
	holidays = [holiday.holiday_date for holiday in holiday_list.holidays]
	return holidays

def is_holiday(date, holidays):
	return getdate(date) in holidays

@frappe.whitelist()
def make_task(source_name, target_doc=None):
	return get_mapped_doc("Issue", source_name, {
		"Issue": {
			"doctype": "Task"
		}
	}, target_doc)

@frappe.whitelist()
def make_issue_from_communication(communication, ignore_communication_links=False):
	""" raise a issue from email """

	doc = frappe.get_doc("Communication", communication)
	issue = frappe.get_doc({
		"doctype": "Issue",
		"subject": doc.subject,
		"communication_medium": doc.communication_medium,
		"raised_by": doc.sender or "",
		"raised_by_phone": doc.phone_no or ""
	}).insert(ignore_permissions=True)

	link_communication_to_document(doc, "Issue", issue.name, ignore_communication_links)

	return issue.name

def get_time_in_timedelta(time):
	"""
		Converts datetime.time(10, 36, 55, 961454) to datetime.timedelta(seconds=38215)
	"""
	import datetime
	return datetime.timedelta(hours=time.hour, minutes=time.minute, seconds=time.second)