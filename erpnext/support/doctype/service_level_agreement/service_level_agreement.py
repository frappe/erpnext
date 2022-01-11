# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form, get_weekdays, getdate, nowdate
from frappe.utils.safe_exec import get_safe_globals


class ServiceLevelAgreement(Document):

	def validate(self):
		self.validate_doc()
		self.check_priorities()
		self.check_support_and_resolution()
		self.validate_condition()

	def check_priorities(self):
		default_priority = []
		priorities = []

		for priority in self.priorities:
			# Check if response and resolution time is set for every priority
			if not priority.response_time or not priority.resolution_time:
				frappe.throw(_("Set Response Time and Resolution Time for Priority {0} in row {1}.").format(priority.priority, priority.idx))

			priorities.append(priority.priority)

			if priority.default_priority:
				default_priority.append(priority.default_priority)

			response = priority.response_time
			resolution = priority.resolution_time

			if response > resolution:
				frappe.throw(_("Response Time for {0} priority in row {1} can't be greater than Resolution Time.").format(priority.priority, priority.idx))

		# Check if repeated priority
		if not len(set(priorities)) == len(priorities):
			repeated_priority = get_repeated(priorities)
			frappe.throw(_("Priority {0} has been repeated.").format(repeated_priority))

		# Check if repeated default priority
		if not len(set(default_priority)) == len(default_priority):
			frappe.throw(_("Select only one Priority as Default."))

		# set default priority from priorities
		try:
			self.default_priority = next(d.priority for d in self.priorities if d.default_priority)
		except Exception:
			frappe.throw(_("Select a Default Priority."))

	def check_support_and_resolution(self):
		week = get_weekdays()
		support_days = []

		for support_and_resolution in self.support_and_resolution:
			# Check if start and end time is set for every support day
			if not (support_and_resolution.start_time or support_and_resolution.end_time):
				frappe.throw(_("Set Start Time and End Time for  \
					Support Day {0} at index {1}.".format(support_and_resolution.workday, support_and_resolution.idx)))

			support_days.append(support_and_resolution.workday)
			support_and_resolution.idx = week.index(support_and_resolution.workday) + 1

			if support_and_resolution.start_time >= support_and_resolution.end_time:
				frappe.throw(_("Start Time can't be greater than or equal to End Time \
					for {0}.".format(support_and_resolution.workday)))

		# Check for repeated workday
		if not len(set(support_days)) == len(support_days):
			repeated_days = get_repeated(support_days)
			frappe.throw(_("Workday {0} has been repeated.").format(repeated_days))

	def validate_doc(self):
		if not frappe.db.get_single_value("Support Settings", "track_service_level_agreement") and self.enable:
			frappe.throw(_("{0} is not enabled in {1}").format(frappe.bold("Track Service Level Agreement"),
				get_link_to_form("Support Settings", "Support Settings")))

		if self.default_service_level_agreement:
			if frappe.db.exists("Service Level Agreement", {"default_service_level_agreement": "1", "name": ["!=", self.name]}):
				frappe.throw(_("A Default Service Level Agreement already exists."))
		else:
			if self.start_date and self.end_date:
				if getdate(self.start_date) >= getdate(self.end_date):
					frappe.throw(_("Start Date of Agreement can't be greater than or equal to End Date."))

				if getdate(self.end_date) < getdate(frappe.utils.getdate()):
					frappe.throw(_("End Date of Agreement can't be less than today."))

		if self.entity_type and self.entity:
			if frappe.db.exists("Service Level Agreement", {"entity_type": self.entity_type, "entity": self.entity, "name": ["!=", self.name]}):
				frappe.throw(_("Service Level Agreement with Entity Type {0} and Entity {1} already exists.").format(self.entity_type, self.entity))

	def validate_condition(self):
		temp_doc = frappe.new_doc('Issue')
		if self.condition:
			try:
				frappe.safe_eval(self.condition, None, get_context(temp_doc))
			except Exception:
				frappe.throw(_("The Condition '{0}' is invalid").format(self.condition))

	def get_service_level_agreement_priority(self, priority):
		priority = frappe.get_doc("Service Level Priority", {"priority": priority, "parent": self.name})

		return frappe._dict({
			"priority": priority.priority,
			"response_time": priority.response_time,
			"resolution_time": priority.resolution_time
		})

def check_agreement_status():
	service_level_agreements = frappe.get_list("Service Level Agreement", filters=[
		{"active": 1},
		{"default_service_level_agreement": 0}
	], fields=["name"])

	for service_level_agreement in service_level_agreements:
		doc = frappe.get_doc("Service Level Agreement", service_level_agreement.name)
		if doc.end_date and getdate(doc.end_date) < getdate(frappe.utils.getdate()):
			frappe.db.set_value("Service Level Agreement", service_level_agreement.name, "active", 0)

def get_active_service_level_agreement_for(doc):
	if not frappe.db.get_single_value("Support Settings", "track_service_level_agreement"):
		return

	filters = [
		["Service Level Agreement", "active", "=", 1],
		["Service Level Agreement", "enable", "=", 1]
	]

	if doc.get('priority'):
		filters.append(["Service Level Priority", "priority", "=", doc.get('priority')])

	customer = doc.get('customer')
	or_filters = [
		["Service Level Agreement", "entity", "in", [customer, get_customer_group(customer), get_customer_territory(customer)]]
	]

	service_level_agreement = doc.get('service_level_agreement')
	if service_level_agreement:
		or_filters = [
			["Service Level Agreement", "name", "=", doc.get('service_level_agreement')],
		]

	default_sla_filter = filters + [["Service Level Agreement", "default_service_level_agreement", "=", 1]]
	default_sla = frappe.get_all("Service Level Agreement", filters=default_sla_filter,
		fields=["name", "default_priority", "condition"])

	filters += [["Service Level Agreement", "default_service_level_agreement", "=", 0]]
	agreements = frappe.get_all("Service Level Agreement", filters=filters, or_filters=or_filters,
		fields=["name", "default_priority", "condition"])

	# check if the current document on which SLA is to be applied fulfills all the conditions
	filtered_agreements = []
	for agreement in agreements:
		condition = agreement.get('condition')
		if not condition or (condition and frappe.safe_eval(condition, None, get_context(doc))):
			filtered_agreements.append(agreement)

	# if any default sla
	filtered_agreements += default_sla

	return filtered_agreements[0] if filtered_agreements else None

def get_context(doc):
	return {"doc": doc.as_dict(), "nowdate": nowdate, "frappe": frappe._dict(utils=get_safe_globals().get("frappe").get("utils"))}

def get_customer_group(customer):
	if customer:
		return frappe.db.get_value("Customer", customer, "customer_group")

def get_customer_territory(customer):
	if customer:
		return frappe.db.get_value("Customer", customer, "territory")

@frappe.whitelist()
def get_service_level_agreement_filters(name, customer=None):
	if not frappe.db.get_single_value("Support Settings", "track_service_level_agreement"):
		return

	filters = [
		["Service Level Agreement", "active", "=", 1],
		["Service Level Agreement", "enable", "=", 1]
	]

	if not customer:
		or_filters = [
			["Service Level Agreement", "default_service_level_agreement", "=", 1]
		]
	else:
		# Include SLA with No Entity and Entity Type
		or_filters = [
			["Service Level Agreement", "entity", "in", [customer, get_customer_group(customer), get_customer_territory(customer), ""]],
			["Service Level Agreement", "default_service_level_agreement", "=", 1]
		]

	return {
		"priority": [priority.priority for priority in frappe.get_list("Service Level Priority", filters={"parent": name}, fields=["priority"])],
		"service_level_agreements": [d.name for d in frappe.get_list("Service Level Agreement", filters=filters, or_filters=or_filters)]
	}

def get_repeated(values):
	unique_list = []
	diff = []
	for value in values:
		if value not in unique_list:
			unique_list.append(str(value))
		else:
			if value not in diff:
				diff.append(str(value))
	return " ".join(diff)
<<<<<<< HEAD
=======


def get_documents_with_active_service_level_agreement():
	sla_doctypes = frappe.cache().hget("service_level_agreement", "active")

	if sla_doctypes is None:
		return set_documents_with_active_service_level_agreement()

	return sla_doctypes


def set_documents_with_active_service_level_agreement():
	active = [sla.document_type for sla in frappe.get_all("Service Level Agreement", fields=["document_type"])]
	frappe.cache().hset("service_level_agreement", "active", active)
	return active


def apply(doc, method=None):
	# Applies SLA to document on validate
	if (
		frappe.flags.in_patch
		or frappe.flags.in_migrate
		or frappe.flags.in_install
		or frappe.flags.in_setup_wizard
		or doc.doctype not in get_documents_with_active_service_level_agreement()
	):
		return

	sla = get_active_service_level_agreement_for(doc)

	if not sla:
		return

	process_sla(doc, sla)


def process_sla(doc, sla):

	if not doc.creation:
		doc.creation = now_datetime(doc.get("owner"))
		if doc.meta.has_field("service_level_agreement_creation"):
			doc.service_level_agreement_creation = now_datetime(doc.get("owner"))

	doc.service_level_agreement = sla.name
	doc.priority = doc.get("priority") or sla.default_priority

	handle_status_change(doc, sla.apply_sla_for_resolution)
	update_response_and_resolution_metrics(doc, sla.apply_sla_for_resolution)
	update_agreement_status(doc, sla.apply_sla_for_resolution)


def handle_status_change(doc, apply_sla_for_resolution):
	now_time = frappe.flags.current_time or now_datetime(doc.get("owner"))
	prev_status = frappe.db.get_value(doc.doctype, doc.name, 'status')

	hold_statuses = get_hold_statuses(doc.service_level_agreement)
	fulfillment_statuses = get_fulfillment_statuses(doc.service_level_agreement)

	def is_hold_status(status):
		return status in hold_statuses

	def is_fulfilled_status(status):
		return status in fulfillment_statuses

	def is_open_status(status):
		return status not in hold_statuses and status not in fulfillment_statuses

	def set_first_response():
		if doc.meta.has_field("first_responded_on") and not doc.get('first_responded_on'):
			doc.first_responded_on = now_time
			if get_datetime(doc.get('first_responded_on')) > get_datetime(doc.get('response_by')):
				record_assigned_users_on_failure(doc)

	def calculate_hold_hours():
		# In case issue was closed and after few days it has been opened
		# The hold time should be calculated from resolution_date

		on_hold_since = doc.resolution_date or doc.on_hold_since
		if on_hold_since:
			current_hold_hours = time_diff_in_seconds(now_time, on_hold_since)
			doc.total_hold_time = (doc.total_hold_time or 0) + current_hold_hours
		doc.on_hold_since = None

	if ((is_open_status(prev_status) and not is_open_status(doc.status)) or doc.flags.on_first_reply):
		set_first_response()

	# Open to Replied
	if is_open_status(prev_status) and is_hold_status(doc.status):
		# Issue is on hold -> Set on_hold_since
		doc.on_hold_since = now_time
		reset_expected_response_and_resolution(doc)

	# Replied to Open
	if is_hold_status(prev_status) and is_open_status(doc.status):
		# Issue was on hold -> Calculate Total Hold Time
		calculate_hold_hours()
		# Issue is open -> reset resolution_date
		reset_resolution_metrics(doc)

	# Open to Closed
	if is_open_status(prev_status) and is_fulfilled_status(doc.status):
		# Issue is closed -> Set resolution_date
		doc.resolution_date = now_time
		set_resolution_time(doc)

	# Closed to Open
	if is_fulfilled_status(prev_status) and is_open_status(doc.status):
		# Issue was closed -> Calculate Total Hold Time from resolution_date
		calculate_hold_hours()
		# Issue is open -> reset resolution_date
		reset_resolution_metrics(doc)

	# Closed to Replied
	if is_fulfilled_status(prev_status) and is_hold_status(doc.status):
		# Issue was closed -> Calculate Total Hold Time from resolution_date
		calculate_hold_hours()
		# Issue is on hold -> Set on_hold_since
		doc.on_hold_since = now_time
		reset_expected_response_and_resolution(doc)

	# Replied to Closed
	if is_hold_status(prev_status) and is_fulfilled_status(doc.status):
		# Issue was on hold -> Calculate Total Hold Time
		calculate_hold_hours()
		# Issue is closed -> Set resolution_date
		if apply_sla_for_resolution:
			doc.resolution_date = now_time
			set_resolution_time(doc)


def get_fulfillment_statuses(service_level_agreement):
	return [entry.status for entry in frappe.db.get_all("SLA Fulfilled On Status", filters={
		"parent": service_level_agreement
	}, fields=["status"])]


def get_hold_statuses(service_level_agreement):
	return [entry.status for entry in frappe.db.get_all("Pause SLA On Status", filters={
		"parent": service_level_agreement
	}, fields=["status"])]


def update_response_and_resolution_metrics(doc, apply_sla_for_resolution):
	priority = get_response_and_resolution_duration(doc)
	start_date_time = get_datetime(doc.get("service_level_agreement_creation") or doc.creation)
	set_response_by(doc, start_date_time, priority)
	if apply_sla_for_resolution and not doc.get('on_hold_since'): # resolution_by is reset if on hold
		set_resolution_by(doc, start_date_time, priority)


def get_expected_time_for(parameter, service_level, start_date_time):
	current_date_time = start_date_time
	expected_time = current_date_time
	start_time = end_time = None
	expected_time_is_set = 0

	allotted_seconds = get_allotted_seconds(parameter, service_level)
	support_days = get_support_days(service_level)
	holidays = get_holidays(service_level.get("holiday_list"))
	weekdays = get_weekdays()

	while not expected_time_is_set:
		current_weekday = weekdays[current_date_time.weekday()]

		if not is_holiday(current_date_time, holidays) and current_weekday in support_days:
			if getdate(current_date_time) == getdate(start_date_time) \
				and get_time_in_timedelta(current_date_time.time()) > support_days[current_weekday].start_time:
				start_time = current_date_time - datetime(current_date_time.year, current_date_time.month, current_date_time.day)
			else:
				start_time = support_days[current_weekday].start_time

			end_time = support_days[current_weekday].end_time
			time_left_today = time_diff_in_seconds(end_time, start_time)
			# no time left for support today
			if time_left_today <= 0:
				pass

			elif allotted_seconds:
				if time_left_today >= allotted_seconds:
					expected_time = datetime.combine(getdate(current_date_time), get_time(start_time))
					expected_time = add_to_date(expected_time, seconds=allotted_seconds)
					expected_time_is_set = 1
				else:
					allotted_seconds = allotted_seconds - time_left_today

		if not expected_time_is_set:
			current_date_time = add_to_date(current_date_time, days=1)

	if end_time and allotted_seconds >= 86400:
		current_date_time = datetime.combine(getdate(current_date_time), get_time(end_time))
	else:
		current_date_time = expected_time

	return current_date_time


def get_allotted_seconds(parameter, service_level):
	allotted_seconds = 0
	if parameter == "response":
		allotted_seconds = service_level.get("response_time")
	elif parameter == "resolution":
		allotted_seconds = service_level.get("resolution_time")
	else:
		frappe.throw(_("{0} parameter is invalid").format(parameter))

	return allotted_seconds


def get_support_days(service_level):
	support_days = {}
	for service in service_level.get("support_and_resolution"):
		support_days[service.workday] = frappe._dict({
			"start_time": service.start_time,
			"end_time": service.end_time,
		})
	return support_days


def set_resolution_time(doc):
	start_date_time = get_datetime(doc.get("service_level_agreement_creation") or doc.creation)
	if doc.meta.has_field("resolution_time"):
		doc.resolution_time = time_diff_in_seconds(doc.resolution_date, start_date_time)

	# total time taken by a user to close the issue apart from wait_time
	if not doc.meta.has_field("user_resolution_time"):
		return

	communications = frappe.get_all("Communication", filters={
			"reference_doctype": doc.doctype,
			"reference_name": doc.name
		}, fields=["sent_or_received", "name", "creation"], order_by="creation")

	pending_time = []
	for i in range(len(communications)):
		if communications[i].sent_or_received == "Received" and communications[i-1].sent_or_received == "Sent":
			wait_time = time_diff_in_seconds(communications[i].creation, communications[i-1].creation)
			if wait_time > 0:
				pending_time.append(wait_time)

	total_pending_time = sum(pending_time)
	resolution_time_in_secs = time_diff_in_seconds(doc.resolution_date, start_date_time)
	doc.user_resolution_time = resolution_time_in_secs - total_pending_time


def change_service_level_agreement_and_priority(self):
	if self.service_level_agreement and frappe.db.exists("Issue", self.name) and \
		frappe.db.get_single_value("Support Settings", "track_service_level_agreement"):

		if not self.priority == frappe.db.get_value("Issue", self.name, "priority"):
			self.set_response_and_resolution_time(priority=self.priority, service_level_agreement=self.service_level_agreement)
			frappe.msgprint(_("Priority has been changed to {0}.").format(self.priority))

		if not self.service_level_agreement == frappe.db.get_value("Issue", self.name, "service_level_agreement"):
			self.set_response_and_resolution_time(priority=self.priority, service_level_agreement=self.service_level_agreement)
			frappe.msgprint(_("Service Level Agreement has been changed to {0}.").format(self.service_level_agreement))


def get_response_and_resolution_duration(doc):
	sla = frappe.get_doc("Service Level Agreement", doc.service_level_agreement)
	priority = sla.get_service_level_agreement_priority(doc.priority)
	priority.update({
		"support_and_resolution": sla.support_and_resolution,
		"holiday_list": sla.holiday_list
	})
	return priority


def reset_service_level_agreement(doc, reason, user):
	if not frappe.db.get_single_value("Support Settings", "allow_resetting_service_level_agreement"):
		frappe.throw(_("Allow Resetting Service Level Agreement from Support Settings."))

	frappe.get_doc({
		"doctype": "Comment",
		"comment_type": "Info",
		"reference_doctype": doc.doctype,
		"reference_name": doc.name,
		"comment_email": user,
		"content": " resetted Service Level Agreement - {0}".format(_(reason)),
	}).insert(ignore_permissions=True)

	doc.service_level_agreement_creation = now_datetime(doc.get("owner"))
	doc.save()


def reset_resolution_metrics(doc):
	if doc.meta.has_field("resolution_date"):
		doc.resolution_date = None

	if doc.meta.has_field("resolution_time"):
		doc.resolution_time = None

	if doc.meta.has_field("user_resolution_time"):
		doc.user_resolution_time = None


# called via hooks on communication update
def on_communication_update(doc, status):
	if doc.communication_type == "Comment":
		return

	parent = get_parent_doc(doc)
	if not parent:
		return

	if not parent.meta.has_field('service_level_agreement'):
		return

	if (
		doc.sent_or_received == "Received" # a reply is received
		and parent.get('status') == 'Open' # issue status is set as open from communication.py
		and parent.get_doc_before_save()
		and parent.get('status') != parent._doc_before_save.get('status') # status changed
	):
		# undo the status change in db
		# since prev status is fetched from db
		frappe.db.set_value(
			parent.doctype, parent.name,
			'status', parent._doc_before_save.get('status'),
			update_modified=False
		)

	elif (
		doc.sent_or_received == "Sent" # a reply is sent
		and parent.get('first_responded_on') # first_responded_on is set from communication.py
		and parent.get_doc_before_save()
		and not parent._doc_before_save.get('first_responded_on') # first_responded_on was not set
	):
		# reset first_responded_on since it will be handled/set later on
		parent.first_responded_on = None
		parent.flags.on_first_reply = True

	else:
		return

	for_resolution = frappe.db.get_value('Service Level Agreement', parent.service_level_agreement, 'apply_sla_for_resolution')

	handle_status_change(parent, for_resolution)
	update_response_and_resolution_metrics(parent, for_resolution)
	update_agreement_status(parent, for_resolution)

	parent.save()


def reset_expected_response_and_resolution(doc):
	if doc.meta.has_field("first_responded_on") and not doc.get('first_responded_on'):
		doc.response_by = None
	if doc.meta.has_field("resolution_by") and not doc.get('resolution_date'):
		doc.resolution_by = None


def set_response_by(doc, start_date_time, priority):
	if doc.meta.has_field("response_by"):
		doc.response_by = get_expected_time_for(parameter="response", service_level=priority, start_date_time=start_date_time)
		if doc.meta.has_field("total_hold_time") and doc.get('total_hold_time') and not doc.get('first_responded_on'):
			doc.response_by = add_to_date(doc.response_by, seconds=round(doc.get('total_hold_time')))


def set_resolution_by(doc, start_date_time, priority):
	if doc.meta.has_field("resolution_by"):
		doc.resolution_by = get_expected_time_for(parameter="resolution", service_level=priority, start_date_time=start_date_time)
		if doc.meta.has_field("total_hold_time") and doc.get('total_hold_time'):
			doc.resolution_by = add_to_date(doc.resolution_by, seconds=round(doc.get('total_hold_time')))


def record_assigned_users_on_failure(doc):
	assigned_users = doc.get_assigned_users()
	if assigned_users:
		from frappe.utils import get_fullname
		assigned_users = ', '.join((get_fullname(user) for user in assigned_users))
		message = _('First Response SLA Failed by {}').format(assigned_users)
		doc.add_comment(
			comment_type='Assigned',
			text=message
		)


def get_service_level_agreement_fields():
	return [
		{
			"collapsible": 1,
			"fieldname": "service_level_section",
			"fieldtype": "Section Break",
			"label": "Service Level"
		},
		{
			"fieldname": "service_level_agreement",
			"fieldtype": "Link",
			"label": "Service Level Agreement",
			"options": "Service Level Agreement"
		},
		{
			"fieldname": "priority",
			"fieldtype": "Link",
			"label": "Priority",
			"options": "Issue Priority"
		},
		{
			"fieldname": "response_by",
			"fieldtype": "Datetime",
			"label": "Response By",
			"read_only": 1
		},
		{
			"fieldname": "first_responded_on",
			"fieldtype": "Datetime",
			"label": "First Responded On",
			"no_copy": 1,
			"read_only": 1
		},
		{
			"fieldname": "on_hold_since",
			"fieldtype": "Datetime",
			"hidden": 1,
			"label": "On Hold Since",
			"read_only": 1
		},
		{
			"fieldname": "total_hold_time",
			"fieldtype": "Duration",
			"label": "Total Hold Time",
			"read_only": 1
		},
		{
			"fieldname": "cb",
			"fieldtype": "Column Break",
			"read_only": 1
		},
		{
			"default": "First Response Due",
			"fieldname": "agreement_status",
			"fieldtype": "Select",
			"label": "Service Level Agreement Status",
			"options": "First Response Due\nResolution Due\nFulfilled\nFailed",
			"read_only": 1
		},
		{
			"fieldname": "resolution_by",
			"fieldtype": "Datetime",
			"label": "Resolution By",
			"read_only": 1
		},
		{
			"fieldname": "service_level_agreement_creation",
			"fieldtype": "Datetime",
			"hidden": 1,
			"label": "Service Level Agreement Creation",
			"read_only": 1
		},
		{
			"depends_on": "eval:!doc.__islocal",
			"fieldname": "resolution_date",
			"fieldtype": "Datetime",
			"label": "Resolution Date",
			"no_copy": 1,
			"read_only": 1
		}
	]


def update_agreement_status_on_custom_status(doc):
	# Update Agreement Fulfilled status using Custom Scripts for Custom Status
	update_agreement_status(doc)


def update_agreement_status(doc, apply_sla_for_resolution):
	if (doc.meta.has_field("agreement_status")):
		# if SLA is applied for resolution check for response and resolution, else only response
		if apply_sla_for_resolution:
			if doc.meta.has_field("first_responded_on") and not doc.get('first_responded_on'):
				doc.agreement_status = "First Response Due"
			elif doc.meta.has_field("resolution_date") and not doc.get('resolution_date'):
				doc.agreement_status = "Resolution Due"
			elif get_datetime(doc.get('resolution_date')) <= get_datetime(doc.get('resolution_by')):
				doc.agreement_status = "Fulfilled"
			else:
				doc.agreement_status = "Failed"
		else:
			if doc.meta.has_field("first_responded_on") and not doc.get('first_responded_on'):
				doc.agreement_status = "First Response Due"
			elif get_datetime(doc.get('first_responded_on')) <= get_datetime(doc.get('response_by')):
				doc.agreement_status = "Fulfilled"
			else:
				doc.agreement_status = "Failed"


def is_holiday(date, holidays):
	return getdate(date) in holidays


def get_time_in_timedelta(time):
	"""Converts datetime.time(10, 36, 55, 961454) to datetime.timedelta(seconds=38215)."""
	import datetime
	return datetime.timedelta(hours=time.hour, minutes=time.minute, seconds=time.second)


def now_datetime(user):
	dt = convert_utc_to_user_timezone(datetime.utcnow(), user)
	return dt.replace(tzinfo=None)


def convert_utc_to_user_timezone(utc_timestamp, user):
	from pytz import UnknownTimeZoneError, timezone

	user_tz = get_tz(user)
	utcnow = timezone('UTC').localize(utc_timestamp)
	try:
		return utcnow.astimezone(timezone(user_tz))
	except UnknownTimeZoneError:
		return utcnow


def get_tz(user):
	return frappe.db.get_value("User", user, "time_zone") or get_time_zone()


@frappe.whitelist()
def get_user_time(user, to_string=False):
	return get_datetime_str(now_datetime(user)) if to_string else now_datetime(user)


@frappe.whitelist()
def get_sla_doctypes():
	doctypes = []
	data = frappe.get_all('Service Level Agreement',
		{'enabled': 1},
		['document_type'],
		distinct=1
	)

	for entry in data:
		doctypes.append(entry.document_type)

	return doctypes
>>>>>>> 2b33e63d2c (fix: use `get_all` instead of `get_list` while fetching SLA doctypes (#29216))
