# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe import utils
from frappe.model.document import Document
from frappe.utils import now, today, time_diff_in_hours, now_datetime, add_days, date_diff, add_to_date, getdate, get_datetime
from frappe.utils.user import is_website_user
import re
from datetime import datetime, timedelta
from itertools import cycle

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
		self.set_support_contract()

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

	def set_support_contract(self):
		if not self.isset_sla:
			support_days = []
			holidays = []
			#Cusotmer find in here
			support_contract = frappe.get_list("Support Contract", filters=[{"customer": self.customer, "contract_status": "Active"}], fields=["name", "contract_template", "service_level", "holiday_list", "priority"], limit=1)
			if not support_contract:
				support_contract = frappe.get_list("Support Contract", filters=[{"default_contract": "1"}], fields=["name", "contract_template", "service_level", "holiday_list", "priority"], limit=1)
			if support_contract:
				self.support_contract = support_contract[0].name
				self.priority = support_contract[0].priority
				service_level = frappe.get_doc("Service Level", support_contract[0].service_level)
				holiday_list = frappe.get_doc("Holiday List", support_contract[0].holiday_list)
				for service in service_level.support_and_resolution:
					day = [service.workday, str(service.start_time), str(service.end_time)]
					support_days.append(day)
				for holiday in holiday_list.holidays:
					holidays.append(holiday.holiday_date)
				for service in service_level.support_and_resolution:
					if service.workday == datetime.now().strftime("%A"):
						self.response_by, self.time_to_respond = self.calculate_support_day(time=service.response_time, time_period=service.response_time_period, support_days=support_days, holidays=holidays)
						self.resolution_by, self.time_to_resolve = self.calculate_support_day(time=service.resolution_time, time_period=service.resolution_time_period, support_days=support_days, holidays=holidays)

	def calculate_support_day(self, time=None, time_period=None, support_days=None, holidays=None):
		week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday','Friday', 'Saturday', 'Sunday']
		now_datetime, add_day, flag, hours = utils.get_datetime(), 0, 0, None

		if time_period == 'Hour/s':
			time, hours = 0, time
		elif time_period == 'Week/s':
			time *= 7
		
		while time != 0:
			for count, weekday in enumerate(week):
				if count >= (now_datetime.date()).weekday() and flag == 0 and time != 0:
					for support_day in support_days:
						if weekday == support_day[0]:
							if weekday == week[len(week)-1]:
								flag = 1
							time -= 1
						elif weekday == week[len(week)-1]:
							flag = 1
					add_day += 1
				elif count < (now_datetime.date()).weekday() and flag == 1 and time != 0:
					for support_day in support_days:
						if weekday == support_day[0]:
							if weekday == week[(now_datetime.date()).weekday()-1]:
								flag = 0
							time -= 1
						elif weekday == week[(now_datetime.date()).weekday()-1]:
							flag = 0
					add_day += 1
		now_datetime += timedelta(days=add_day)

		print("-------------------------------------------------------------------------------")
		print("Final Time : ===================================" + str(now_datetime) + "=============" + str(week[(now_datetime.date()).weekday()]))
		print("-------------------------------------------------------------------------------")
		support = self.calculate_support_time(time=now_datetime, hours=hours, support_days=support_days, holidays=holidays, week=week)
		return support, time_diff_in_hours(support, utils.now_datetime())
		
	def calculate_support_time(self, time=None, hours=None, support_days=None, holidays=None, week=None):
		time_difference, flag, loop, time_add = 0, 0, None, 0
		while loop != 'set':
			for count, weekday in enumerate(week):
				if count >= (time.date()).weekday() and flag == 0 and loop != 'set':	#	To search the week from the current weekday
					for support_day in support_days:									#	Check if the day is in the support day
						if weekday == support_day[0]:
							print("Checking day Loop 1---------- " + support_day[0])
							
							start_time, end_time = datetime.strptime(support_day[1], '%H:%M:%S').time(), datetime.strptime(support_day[2], '%H:%M:%S').time()
							print("---------------------------" + str(time))

							if time.time() <= end_time and time.time() >= start_time and hours and time_add == 0: #	Add hours to time if the time is between start and end time orelse it'll add one more day to the count
								time += timedelta(hours=hours)
								time_add = 1

							if time_difference:										#	Add time difference at every loop iteration
								time = datetime.combine(time.date(), start_time)
								time += timedelta(seconds=time_difference)

							if time.time() <= end_time and time.time() >= start_time:	#	If computed time is between start and end time then stop execution
								if not hours:											#	If hours is None then append end time to the time
									time = datetime.combine(time.date(), end_time)
								if time.date() in holidays:								#	If date is in holidays then continue
									continue
								loop = 'set'											#	Flag to stop while loop execution
								break
							elif time.time() <= start_time:								#	Time is before start time
								if hours and time_add == 0:								#	If hours then add hours to start time
									time = datetime.combine(time.date(), start_time)
									time += timedelta(hours=hours)
									time_add = 1										#	Flag to stop adding of hours once
								if not hours:
									time = datetime.combine(time.date(), end_time)		#	If computed hours if before start time then append end time of that day to computed time
								else:
									time_difference = (time - datetime.combine(time.date()-timedelta(days=1), datetime.strptime(support_days[support_days.index(support_day)][2], '%H:%M:%S').time())).total_seconds() #	Compute the time difference
									print("time_difference_smaller" + str(time_difference/3600))
									print(support_days[support_days.index(support_day)][2])
								if time.date() in holidays:
									continue
								print("*** " + str(time))
							elif time.time() >= end_time:
								if hours and time_add == 0:
									time = datetime.combine(time.date()+timedelta(days=1), start_time)
									time += timedelta(hours=hours)
									time_add = 1
								if not hours:
									time = datetime.combine(time.date(), end_time)
								else:
									time_difference = (time - datetime.combine(time.date(), end_time)).total_seconds()
									print("time_difference_greater" + str(time_difference/3600))
								if time.date() in holidays:
									continue
								print("*** " + str(time))

							if weekday == week[len(week)-1]:
								flag = 1
							if time.time() <= end_time and time.time() >= start_time:
								loop = 'set'
								break

						elif weekday == week[len(week)-1]:
							flag = 1
					if loop != 'set':
						time += timedelta(days=1)
					print(time)
				elif count <= (time.date()).weekday() and flag == 1 and loop != 'set':
					for support_day in support_days:
						if weekday == support_day[0]:
							print("Checking day Loop 2---------- " + support_day[0])
							print("--- " + str(time))
							
							start_time, end_time = datetime.strptime(support_day[1], '%H:%M:%S').time(), datetime.strptime(support_day[2], '%H:%M:%S').time()
							if time.time() <= end_time and time.time() >= start_time and hours and time_add == 0:
								time += timedelta(hours=hours)
								time_add = 1
							if time_difference:
								time = datetime.combine(time.date(), start_time)
								time += timedelta(seconds=time_difference)

							if time.time() <= end_time and time.time() >= start_time:
								if hours and time_add == 0:
									time += timedelta(hours=hours)
									time_add = 1
									if time.time() >= end_time or time.time() <= start_time:
										print("IN HERE")
										continue
								if not hours:
									time = datetime.combine(time.date(), end_time)
								if time.date() in holidays:
									continue
								loop = 'set'
								break

							elif time.time() <= start_time:
								if hours and time_add == 0:
									time = datetime.combine(time.date(), start_time)
									time += timedelta(hours=hours)
									time_add = 1
								if not hours:
									time = datetime.combine(time.date(), end_time)
								else:
									time_difference = (time - datetime.combine(time.date()-timedelta(days=1), datetime.strptime(support_days[support_days.index(support_day)][2], '%H:%M:%S').time())).total_seconds()
									print("time_difference_smaller" + str(time_difference/3600))
									print(support_days[support_days.index(support_day)][2])
								print("*** " + str(time))
								if time.date() in holidays:
									continue

							elif time.time() >= end_time:
								if hours and time_add == 0:
									time = datetime.combine(time.date()+timedelta(days=1), start_time)
									time += timedelta(hours=hours)
									time_add = 1
								if not hours:
									time = datetime.combine(time.date(), end_time)
								else:
									time_difference = (time - datetime.combine(time.date(), end_time)).total_seconds()
									print("time_difference_greater" + str(time_difference/3600))
								print("*** " + str(time))
								if time.date() in holidays:
									continue
								
							if weekday == week[(time.date()).weekday()-1]:
								flag = 0
							if time.time() <= end_time and time.time() >= start_time:
								loop = 'set'
								break
						elif weekday == week[(time.date()).weekday()-1]:
							flag = 0
					if loop != 'set':
						time += timedelta(days=1)
					print(time)
		print("*****************************************************************************************")		

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
	for issue in issues:
		doc = frappe.get_doc("Issue", issue.name)
		if float(doc.time_to_respond) > 0 and not doc.first_responded_on:
			doc.time_to_respond = time_diff_in_hours(doc.response_by, utils.now_datetime())
		if float(doc.time_to_resolve) > 0:
			doc.time_to_resolve = time_diff_in_hours(doc.resolution_by, utils.now_datetime())
		else:
			doc.service_contract_status = "Failed"
		doc.save()

#	def calculate_support_time_day(self, response_time=None, response_time_period=None, resolution_time=None, resolution_time_period=None, support_days=None):
#
#		#Calculation on Time to Respond
#		if response_time_period == 'Hour/s':
#			response_by = self.calculate_support_time(time=add_to_date(utils.now_datetime(), hours=int(response_time), as_datetime=True), support_days=support_days)
#			self.response_by = response_by
#			self.time_to_respond = 24 * date_diff(response_by, utils.now_datetime())
#			#print("==:= reply by : " + str(add_to_date(utils.now_datetime(), hours=int(response_time), as_datetime=True)))
#			#print("==:= reply by : " + str(response_by))
#
#		elif response_time_period == 'Day/s':
#			response_by = self.calculate_support_time(time=add_to_date(utils.now_datetime(), hours=24 * int(response_time), as_datetime=True), support_days=support_days)
#			self.response_by = response_by
#			self.time_to_respond = 24 * date_diff(response_by, utils.now_datetime())
#			#print("==:= reply by : " + add_to_date(utils.now_datetime(), hours=24 * int(response_time), as_datetime=True))
#			#print("==:= reply by : " + str(response_by))
#
#		elif response_time_period == 'Week/s':
#			response_by = self.calculate_support_time(time=add_to_date(utils.now_datetime(), hours=7 * 24 * int(response_time), as_datetime=True), support_days=support_days)
#			self.response_by = response_by
#			self.time_to_respond = 24 * date_diff(response_by, utils.now_datetime())
#			#print("==:= reply by : " + add_to_date(utils.now_datetime(), hours=7 * 24 * int(response_time), as_datetime=True))
#			#print("==:= reply by : " + str(response_by))
#		
#		#Calculation of Time to Resolve
#		if resolution_time_period == 'Hour/s':
#			resolution_by = self.calculate_support_time(time=add_to_date(utils.now_datetime(), hours=int(resolution_time), as_datetime=True), support_days=support_days)
#			self.resolution_by = resolution_by
#			self.time_to_resolve = 24 * date_diff(resolution_by, utils.now_datetime())
#			#print("==:= reply by : " + str(add_to_date(utils.now_datetime(), hours=int(resolution_time), as_datetime=True)))
#			#print("==:= reply by : " + str(resolution_by))
#			
#		elif resolution_time_period == 'Day/s':
#			resolution_by = self.calculate_support_time(time=add_to_date(utils.now_datetime(), hours=24 * int(resolution_time), as_datetime=True), support_days=support_days)
#			self.resolution_by = resolution_by
#			self.time_to_resolve = 24 * date_diff(resolution_by, utils.now_datetime())
#			#print("==:= reply by : " + str(add_to_date(utils.now_datetime(), hours=24 * int(resolution_time), as_datetime=True)))
#			#print("==:= reply by : " + str(resolution_by))
#			
#		else:
#			resolution_by = self.calculate_support_time(time=add_to_date(utils.now_datetime(), hours=7 * 24 * int(resolution_time), as_datetime=True), support_days=support_days)
#			self.resolution_by = resolution_by
#			self.time_to_resolve = 24 * date_diff(resolution_by, utils.now_datetime())
#			#print("==:= reply by : " + str(add_to_date(utils.now_datetime(), hours=7 * 24 * int(resolution_time), as_datetime=True)))
#			#print("==:= reply by : " + str(resolution_by))
#	
#		issue_criticality = frappe.get_list("Issue Criticality")
#		for criticality in issue_criticality:
#			criticality_doc = frappe.get_doc("Issue Criticality", criticality)
#			for keyword in criticality_doc.keyword:
#				if re.search(r''+ keyword.keyword +'', self.subject, re.IGNORECASE):
#					self.priority = criticality_doc.priority
#					self.isset_sla = 1


#	def calculate_support_time(self, time=None, support_days=None):
#		week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday','Friday', 'Saturday', 'Sunday']
#		flag = None
#		time_difference_greater = None
#		time_difference_smaller = None
#		day_difference = 0
#		reply = time
#		print("*****************************************************************************************")
#		print("Loop 1")
#		for count, weekday in enumerate(week):
#			if flag == "set":
#				break
#			if count >= (time.date()).weekday():
#				for support_day in support_days:
#					if weekday == support_day[0]:
#						start_time = datetime.strptime(support_day[1], '%H:%M:%S').time()
#						end_time = datetime.strptime(support_day[2], '%H:%M:%S').time()
#						if time.time() > end_time and time_difference_greater == None:
#							print("IF - 1	")
#							time_difference_greater = (datetime.combine(time.date(), time.time()) - datetime.combine(time.date(), end_time)).total_seconds()
#							print("Greater Time : " + str(time_difference_greater/3600))
#						elif time.time() < start_time and time_difference_smaller == None:
#							print("ELIF - 1	")
#							time_difference_smaller =  (datetime.combine(time.date(), start_time) - datetime.combine(time.date(), time.time())).total_seconds()
#							print("Smaller Time : " + str(time_difference_smaller/3600))
#						else:
#							print("ELSE - 1	")
#							reply += timedelta(days=day_difference)
#							if time_difference_greater != None:
#								reply = datetime.combine(reply.date(), start_time)
#								reply += timedelta(seconds=time_difference_greater)
#							flag = "set"
#							break
#				day_difference += 1
#		if flag == None:
#			print("Loop 2")
#			for count, weekday in enumerate(week):
#				if flag == "set":
#					break
#				if count <= (time.date()).weekday():
#					for support_day in support_days:
#						if weekday == support_day[0]:
#							start_time = datetime.strptime(support_day[1], '%H:%M:%S').time()
#							end_time = datetime.strptime(support_day[2], '%H:%M:%S').time()
#							if time.time() > end_time and time_difference_greater == None:
#								print("IF - 2")
#								time_difference_greater = (datetime.combine(time.date(), time.time()) - datetime.combine(time.date(), end_time)).total_seconds()
#								print("Greater Time : " + str(time_difference_greater/3600))
#							elif time.time() < start_time and time_difference_smaller == None:
#								print("ELIF - 2	")
#								time_difference_smaller =  (datetime.combine(time.date(), start_time) - datetime.combine(time.date(), time.time())).total_seconds()
#								print("Smaller Time : " + str(time_difference_smaller/3600))
#							else:
#								print("ELSE - 2")
#								reply += timedelta(days=day_difference)
#								if time_difference_greater != None:
#									reply = datetime.combine(reply.date(), start_time)
#									reply += timedelta(seconds=time_difference_greater)
#								flag = "set"
#								break
#					day_difference += 1
##		print("*****************************************************************************************")
##		return reply
#
#	def calculate_support_day(self, time=None, time_period=None, support_days=None):
#		week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday','Friday', 'Saturday', 'Sunday']
#		now_datetime = utils.get_datetime()
#		if time_period == 'Hour/s':
#			now_datetime += timedelta(hours=int(time))
#		else:
#			if time_period == 'Week/s':
#				time *= 7
##			elif time_period == 'Hour/s':
##				time, hours = 1, time
#			add_day = 0#-1 #because same day is counted as zero
#			loop = None
#			flag = 0
#			while loop != 'set':
#				for count, weekday in enumerate(week):
#					if time == 0:
#						loop = 'set'
#						break
#					elif count >= (now_datetime.date()).weekday() and flag == 0 and time != 0:
#						for support_day in support_days:
#							if weekday == support_day[0]:
#								if weekday == week[len(week)-1]:
#									flag = 1
#								time -= 1
#							elif weekday == week[len(week)-1]:
#								flag = 1
#						add_day += 1
#					elif count < (now_datetime.date()).weekday() and flag == 1 and time != 0:
#						for support_day in support_days:
#							if weekday == support_day[0]:
#								if weekday == week[(now_datetime.date()).weekday()-1]:
#									flag = 0
#								time -= 1
#							elif weekday == week[(now_datetime.date()).weekday()-1]:
#								flag = 0
#						add_day += 1
#			now_datetime += timedelta(days=add_day)
#		print("-------------------------------------------------------------------------------")
#		print("Final Time : ===================================" + str(now_datetime) + "=============" + str(week[(now_datetime.date()).weekday()]))
#		print("-------------------------------------------------------------------------------")
#		calc_supp = self.calculate_support1(time=now_datetime, support_days=support_days)
#		return calc_supp, time_diff_in_hours(calc_supp, utils.now_datetime())
#		
#	def calculate_support1(self, time=None, support_days=None):
#		week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday','Friday', 'Saturday', 'Sunday']
#		time_difference = 0
#		flag = 0
#		print("*****************************************************************************************")
#		loop = None
#		while loop != 'set':
#			for count, weekday in enumerate(week):
#				if loop == "set":
#					break
#				elif count >= (time.date()).weekday() and flag == 0 and loop != 'set':
#					print(weekday)
#					for support_day in support_days:
#						if weekday == support_day[0]:
#							print("Checking day Loop 1---------- " + support_day[0])
#							print("--- " + str(time))
#							start_time = datetime.strptime(support_day[1], '%H:%M:%S').time()
#							end_time = datetime.strptime(support_day[2], '%H:%M:%S').time()
#							if time_difference:
#								time = datetime.combine(time.date(), start_time)
#								time += timedelta(seconds=time_difference)
#							if time.time() <= end_time and time.time() >= start_time:
#								loop = 'set'
#								break
#							elif time.time() <= start_time:
#								#time_difference = (datetime.combine(time.date(), start_time) - datetime.combine(time.date()-timedelta(days=1), datetime.strptime(support_days[support_days.index(support_day)-1][2], '%H:%M:%S').time())).total_seconds()
#								time_difference = (time - datetime.combine(time.date()-timedelta(days=1), datetime.strptime(support_days[support_days.index(support_day)][2], '%H:%M:%S').time())).total_seconds()
#								print("time_difference_smaller" + str(time_difference/3600))
#								if weekday == week[len(week)-1]:
#									flag = 1
#								print("*** " + str(time))
#								if time.time() <= end_time and time.time() >= start_time:
#									loop = 'set'
#									break
#							elif time.time() >= end_time:
#								time_difference = (time - datetime.combine(time.date(), end_time)).total_seconds()
#								print("time_difference_greater" + str(time_difference/3600))
#								if weekday == week[len(week)-1]:
#									flag = 1
#								print("*** " + str(time))
#								if time.time() <= end_time and time.time() >= start_time:
#									loop = 'set'
#									break
#						elif weekday == week[len(week)-1]:
#							flag = 1
#					if loop != 'set':
#						time += timedelta(days=1)
#					print(time)
#				elif count <= (time.date()).weekday() and flag == 1 and loop != 'set':
#					print(weekday)
#					for support_day in support_days:
#						if weekday == support_day[0]:
#							print("Checking day Loop 2---------- " + support_day[0])
#							print("--- " + str(time))
#							start_time = datetime.strptime(support_day[1], '%H:%M:%S').time()
#							end_time = datetime.strptime(support_day[2], '%H:%M:%S').time()
#							if time_difference:
#								time = datetime.combine(time.date(), start_time)
#								time += timedelta(seconds=time_difference)
#							if time.time() <= end_time and time.time() >= start_time:
#								loop = 'set'
#								break
#							elif time.time() <= start_time:
#								#time_difference = (datetime.combine(time.date(), start_time) - datetime.combine(time.date()-timedelta(days=1), datetime.strptime(support_days[support_days.index(support_day)-1][2], '%H:%M:%S').time())).total_seconds()
#								time_difference = (time - datetime.combine(time.date()-timedelta(days=1), datetime.strptime(support_days[support_days.index(support_day)][2], '%H:%M:%S').time())).total_seconds()
#								print("time_difference_smaller" + str(time_difference/3600))
#								if weekday == week[(time.date()).weekday()-1]:
#									flag = 0
#								print("*** " + str(time))
#								if time.time() <= end_time and time.time() >= start_time:
#									loop = 'set'
#									break
#							elif time.time() >= end_time:
#								time_difference = (time - datetime.combine(time.date(), end_time)).total_seconds()
#								print("time_difference_greater" + str(time_difference/3600))
#								if weekday == week[(time.date()).weekday()-1]:
#									flag = 0
#								print("*** " + str(time))
#								if time.time() <= end_time and time.time() >= start_time:
#									loop = 'set'
#									break
#						elif weekday == week[(time.date()).weekday()-1]:
#							flag = 0
#					if loop != 'set':
#						time += timedelta(days=1)
#					print(time)
#		print("*****************************************************************************************")
#		return time