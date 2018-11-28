# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe import utils
from frappe.model.document import Document
from frappe.utils import now, today, time_diff_in_hours, now_datetime
from frappe.utils.user import is_website_user
import re
from datetime import datetime, timedelta

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
		self.set_sla()

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

	def set_sla(self):
		if not self.isset_sla:
			support_contract = frappe.get_list("Support Contract", filters=[{"customer": self.customer, "contract_status": "Active"}], fields=["name", "contract_template", "service_level"], limit=1)
			if support_contract:
				self.support_contract = support_contract[0].name
				service_level = frappe.get_doc("Service Level", support_contract[0].service_level)
				for service in service_level.support_and_resolution:
					if service.day == "Workday" and service.weekday == datetime.now().strftime("%A"):
						self.set_criticality()
					elif service.day == "Holiday" and service.holiday:
						holiday_list = frappe.get_doc("Holiday List", ""+ str(service.holiday) +"")
						for holiday in holiday_list.holidays:
							if holiday.holiday_date == utils.today():
								self.set_criticality()
				self.sla_timer(service.response_time, service.response_time_period, service.resolution_time, service.resolution_time_period)
			else:
				pass

	def sla_timer(self, response_time=None, response_time_period=None, resolution_time=None, resolution_time_period=None):
		if response_time and resolution_time_period and resolution_time and resolution_time_period:
			self.response_time = response_time
			self.response_time_period = response_time_period
			self.resolution_time = resolution_time
			self.resolution_time_period = resolution_time_period
			print(utils.now())
			print(utils.today())
			print(utils.nowdate())
			print(utils.nowtime())
			if response_time == 'Hour/s':
				pass
			elif response_time == 'Day/s':
				pass
			elif response_time == 'Week/s':
				pass
			elif response_time == 'Month/s':
				pass
		else:
			pass

	def set_criticality(self):
		if self.description:
			issue_criticality = frappe.get_list("Issue Criticality")
			for criticality in issue_criticality:
				doc = frappe.get_doc("Issue Criticality", criticality)
				for keyword in doc.keyword:
					if re.search(r''+ keyword.keyword +'', self.description):
						self.issue_criticality = doc.name
						self.employee_group = doc.employee_group
						self.priority = doc.priority
						self.isset_sla = 1

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
