# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import today, getdate, cint
from frappe.model.mapper import get_mapped_doc
from frappe.email.inbox import link_communication_to_document
from frappe.contacts.doctype.address.address import get_default_address
from frappe.contacts.doctype.contact.contact import get_default_contact
from erpnext.stock.get_item_details import get_applies_to_details
from erpnext.setup.utils import get_exchange_rate
from erpnext.utilities.transaction_base import TransactionBase
from erpnext.accounts.party import get_contact_details, get_address_display, get_party_account_currency
from erpnext.crm.doctype.lead.lead import get_customer_from_lead, add_sales_person_from_source
from six import string_types
import json


subject_field = "title"
sender_field = "contact_email"

force_party_fields = [
	'customer_name', 'tax_id', 'tax_cnic', 'tax_strn', 'customer_group', 'territory',
	'address_display', 'contact_display', 'contact_email', 'contact_mobile', 'contact_phone'
]

force_item_fields = ("item_group", "brand")

force_applies_to_fields = [
	"vehicle_chassis_no", "vehicle_engine_no", "vehicle_license_plate", "vehicle_unregistered",
	"vehicle_color", "applies_to_item", "applies_to_item_name", "applies_to_variant_of", "applies_to_variant_of_name"
]


class Opportunity(TransactionBase):
	def get_feed(self):
		return _("From {0}").format(self.get("customer_name") or self.get('party_name'))

	def onload(self):
		if self.opportunity_from == "Customer":
			self.set_onload('customer', self.party_name)
		elif self.opportunity_from == "Lead":
			self.set_onload('customer', get_customer_from_lead(self.party_name))

	def validate(self):
		self.set_missing_values()
		self.validate_uom_is_integer("uom", "qty")
		self.validate_financer()
		self.validate_follow_up()
		self.validate_maintenance_schedule()
		self.set_status()
		self.set_title()

	def after_insert(self):
		self.update_lead_status()

	def on_trash(self):
		self.delete_events()

	def set_title(self):
		self.title = self.customer_name
		if self.contact_display != self.customer_name:
			self.title += " ({0})".format(self.contact_display)

	def set_status(self, update=False, status=None, update_modified=True):
		previous_status = self.status

		if status:
			self.status = status

		has_active_quotation = self.has_active_quotation()

		if self.is_converted():
			self.status = "Converted"
		elif self.status == "Closed":
			self.status = "Closed"
		elif self.status == "Lost" or (not has_active_quotation and self.has_lost_quotation()):
			self.status = "Lost"
		elif self.get('next_follow_up') and getdate(self.next_follow_up) >= getdate():
			self.status = "To Follow Up"
		elif has_active_quotation:
			self.status = "Quotation"
		elif self.has_communication():
			self.status = "Replied"
		else:
			self.status = "Open"

		self.add_status_comment(previous_status)

		if update:
			self.db_set('status', self.status, update_modified=update_modified)

	def set_missing_values(self):
		self.set_customer_details()
		self.set_item_details()
		self.set_applies_to_details()

	def set_customer_details(self):
		customer_details = get_customer_details(self.as_dict())
		for k, v in customer_details.items():
			if self.meta.has_field(k) and (not self.get(k) or k in force_party_fields):
				self.set(k, v)

	def set_item_details(self):
		for d in self.items:
			if not d.item_code:
				continue

			item_details = get_item_details(d.item_code)
			for k, v in item_details.items():
				if d.meta.has_field(k) and (not d.get(k) or k in force_party_fields):
					d.set(k, v)

	def set_applies_to_details(self):
		if self.get("applies_to_vehicle"):
			self.applies_to_serial_no = self.applies_to_vehicle

		args = self.as_dict()
		applies_to_details = get_applies_to_details(args, for_validate=True)

		for k, v in applies_to_details.items():
			if self.meta.has_field(k) and not self.get(k) or k in force_applies_to_fields:
				self.set(k, v)

	def validate_financer(self):
		if self.get('financer'):
			if self.get('opportunity_from') == "Customer" and self.get('party_name') == self.get('financer'):
				frappe.throw(_("Customer and Financer cannot be the same"))

		elif self.meta.has_field('financer'):
			self.financer_name = None
			self.finance_type = None

	def validate_follow_up(self):
		if not self.get('contact_schedule'):
			return

		self.next_follow_up = self.get_next_follow_up_date()

		for d in self.get('contact_schedule'):
			if not d.get('contact_date') and not d.get('schedule_date'):
				frappe.throw(_("Row #{0}: Please set Contact or Schedule Date in follow up".format(d.idx)))

			if d.is_new() and not d.get('contact_date') and getdate(d.get('schedule_date')) < getdate(today()):
				frappe.throw(_("Row #{0}: Can't schedule a follow up for past dates".format(d.idx)))

	def get_next_follow_up_date(self):
		follow_up = [f for f in self.contact_schedule
			if f.schedule_date and not f.contact_date and getdate(f.schedule_date) >= getdate()]

		return getdate(follow_up[0].schedule_date) if follow_up else None

	def validate_maintenance_schedule(self):
		if not self.maintenance_schedule:
			return

		filters = {
			'maintenance_schedule': self.maintenance_schedule,
			'maintenance_schedule_row': self.maintenance_schedule_row
		}
		if not self.is_new():
			filters['name'] = ['!=', self.name]

		dup = frappe.get_value("Opportunity", filters=filters)
		if dup:
			frappe.throw(_("{0} already exists for this scheduled maintenance".format(frappe.get_desk_link("Opportunity", dup))))

	@frappe.whitelist()
	def set_is_lost(self, is_lost, lost_reasons_list=None, detailed_reason=None):
		is_lost = cint(is_lost)

		if is_lost and (self.has_active_quotation() or self.is_converted()):
			frappe.throw(_("Cannot declare as Lost because there are active documents against Opportunity"))

		if is_lost:
			self.set_status(update=True, status="Lost")

			if detailed_reason:
				self.db_set("order_lost_reason", detailed_reason)

			for reason in lost_reasons_list:
				row = self.append('lost_reasons', reason)
				row.db_insert()
		else:
			self.set_status(update=True, status="Open")
			self.db_set('order_lost_reason', None)
			self.lost_reasons = []
			self.update_child_table("lost_reasons")

		self.notify_update()

	def update_lead_status(self):
		if self.opportunity_from == "Lead" and self.party_name:
			doc = frappe.get_doc("Lead", self.party_name)
			doc.set_status(update=True)
			doc.notify_update()

	def has_active_quotation(self):
		vehicle_quotation = get_active_vehicle_quotation(self.name, include_draft=False)

		quotation = frappe.get_all('Quotation', {
			'opportunity': self.name,
			'status': ("not in", ['Lost', 'Closed']),
			'docstatus': 1
		}, 'name')

		return quotation or vehicle_quotation

	def is_converted(self):
		if self.has_ordered_quotation():
			return True

		vehicle_booking_order = get_vehicle_booking_order(self.name, include_draft=False)
		if vehicle_booking_order:
			return True

		appointment = frappe.db.get_value("Appointment", {
			"opportunity": self.name,
			"docstatus": 1,
		})

		if appointment:
			return True

		return False

	def has_ordered_quotation(self):
		quotation = frappe.db.get_value("Quotation", {
			"opportunity": self.name,
			"docstatus": 1,
			"status": "Ordered",
		})

		return quotation

	def has_lost_quotation(self):
		lost_vehicle_quotation = frappe.db.get_value("Vehicle Quotation", {
			"opportunity": self.name,
			"docstatus": 1,
			"status": 'Lost'
		})

		lost_quotation = frappe.db.get_value("Quotation", {
			"opportunity": self.name,
			"docstatus": 1,
			"status": 'Lost'
		})

		if lost_quotation or lost_vehicle_quotation:
			if self.has_active_quotation():
				return False
			return True

	def has_communication(self):
		return frappe.get_value("Communication", filters={'reference_doctype': self.doctype, 'reference_name': self.name})


@frappe.whitelist()
def get_customer_details(args):
	if isinstance(args, string_types):
		args = json.loads(args)

	args = frappe._dict(args)
	out = frappe._dict()

	if not args.opportunity_from or not args.party_name:
		frappe.throw(_("Party is mandatory"))

	if args.opportunity_from not in ['Customer', 'Lead']:
		frappe.throw(_("Opportunity From must be either Customer or Lead"))

	party = frappe.get_cached_doc(args.opportunity_from, args.party_name)

	# Customer Name
	if party.doctype == "Lead":
		out.customer_name = party.company_name or party.lead_name
	else:
		out.customer_name = party.customer_name

	# Tax IDs
	out.tax_id = party.get('tax_id')
	out.tax_cnic = party.get('tax_cnic')
	out.tax_strn = party.get('tax_strn')

	lead = party if party.doctype == "Lead" else None

	# Address
	out.customer_address = args.customer_address or get_default_address(party.doctype, party.name)
	out.address_display = get_address_display(out.customer_address, lead=lead)

	# Contact
	out.contact_person = args.contact_person or get_default_contact(party.doctype, party.name)
	out.update(get_contact_details(out.contact_person, lead=lead))

	out.territory = party.territory
	if party.doctype == "Lead":
		out.sales_person = party.sales_person
		out.source = party.source
		out.campaign = party.campaign

	return out


@frappe.whitelist()
def get_item_details(item_code):
	item_details = frappe.get_cached_doc("Item", item_code) if item_code else frappe._dict()

	return {
		'item_name': item_details.item_name,
		'description': item_details.description,
		'uom': item_details.stock_uom,
		'image': item_details.image,
		'item_group': item_details.item_group,
		'brand': item_details.brand,
	}


@frappe.whitelist()
def make_quotation(source_name, target_doc=None):
	def set_missing_values(source, target):
		company_currency = frappe.get_cached_value('Company',  target.company,  "default_currency")

		if target.quotation_to == 'Customer' and target.party_name:
			party_account_currency = get_party_account_currency("Customer", target.party_name, target.company)
		else:
			party_account_currency = company_currency

		target.currency = party_account_currency or company_currency

		if company_currency == target.currency:
			exchange_rate = 1
		else:
			exchange_rate = get_exchange_rate(target.currency, company_currency,
				target.transaction_date, args="for_selling")

		target.conversion_rate = exchange_rate

		target.run_method("set_missing_values")
		target.run_method("reset_taxes_and_charges")
		target.run_method("calculate_taxes_and_totals")

	doclist = get_mapped_doc("Opportunity", source_name, {
		"Opportunity": {
			"doctype": "Quotation",
			"field_map": {
				"opportunity_from": "quotation_to",
				"opportunity_type": "order_type",
				"name": "opportunity",
				"applies_to_serial_no": "applies_to_serial_no",
				"applies_to_vehicle": "applies_to_vehicle",
			}
		},
		"Opportunity Item": {
			"doctype": "Quotation Item",
			"field_map": {
				"uom": "stock_uom",
			},
			"add_if_empty": True
		}
	}, target_doc, set_missing_values)

	return doclist


@frappe.whitelist()
def make_request_for_quotation(source_name, target_doc=None):
	doclist = get_mapped_doc("Opportunity", source_name, {
		"Opportunity": {
			"doctype": "Request for Quotation"
		},
		"Opportunity Item": {
			"doctype": "Request for Quotation Item",
			"field_map": [
				["name", "opportunity_item"],
				["parent", "opportunity"],
				["uom", "uom"]
			]
		}
	}, target_doc)

	return doclist


@frappe.whitelist()
def make_vehicle_quotation(source_name, target_doc=None):
	existing_quotation = get_active_vehicle_quotation(source_name, include_draft=True)
	if existing_quotation:
		frappe.throw(_("{0} already exists against Opportunity")
			.format(frappe.get_desk_link("Vehicle Quotation", existing_quotation)))

	def set_missing_values(source, target):
		add_sales_person_from_source(source, target)

		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")

	target_doc = get_mapped_doc("Opportunity", source_name, {
		"Opportunity": {
			"doctype": "Vehicle Quotation",
			"field_map": {
				"opportunity_from": "quotation_to",
				"name": "opportunity",
				"applies_to_item": "item_code",
				"applies_to_vehicle": "vehicle",
				"vehicle_color": "color",
				"delivery_period": "delivery_period",
			}
		}
	}, target_doc, set_missing_values)

	return target_doc


@frappe.whitelist()
def make_vehicle_booking_order(source_name, target_doc=None):
	existing_vbo = get_vehicle_booking_order(source_name, include_draft=True)
	if existing_vbo:
		frappe.throw(_("{0} already exists against Opportunity")
			.format(frappe.get_desk_link("Vehicle Booking Order", existing_vbo)))

	def set_missing_values(source, target):
		customer = get_customer_from_opportunity(source)
		if customer:
			target.customer = customer.name
			target.customer_name = customer.customer_name

		add_sales_person_from_source(source, target)

		existing_quotation = get_active_vehicle_quotation(source_name, include_draft=False)
		if existing_quotation:
			target.vehicle_quotation = existing_quotation

		target.run_method("set_missing_values")
		target.run_method("calculate_taxes_and_totals")
		target.run_method("set_payment_schedule")
		target.run_method("set_due_date")

	target_doc = get_mapped_doc("Opportunity", source_name, {
		"Opportunity": {
			"doctype": "Vehicle Booking Order",
			"field_map": {
				"name": "opportunity",
				"applies_to_item": "item_code",
				"applies_to_vehicle": "vehicle",
				"vehicle_color": "color_1",
				"delivery_period": "delivery_period",
			}
		},
	}, target_doc, set_missing_values)

	return target_doc


@frappe.whitelist()
def make_appointment(source_name, target_doc=None):
	def set_missing_values(source, target):
		default_appointment_type = frappe.get_cached_value("Opportunity Type", source.opportunity_type, "default_appointment_type")
		if default_appointment_type:
			target.appointment_type = default_appointment_type

		target.run_method("set_missing_values")

	target_doc = get_mapped_doc("Opportunity", source_name, {
		"Opportunity": {
			"doctype": "Appointment",
			"field_map": {
				"name": "opportunity",
				"applies_to_vehicle": "applies_to_vehicle",
				"applies_to_serial_no": "applies_to_serial_no"
			}
		}
	}, target_doc, set_missing_values)

	return target_doc


@frappe.whitelist()
def make_supplier_quotation(source_name, target_doc=None):
	doclist = get_mapped_doc("Opportunity", source_name, {
		"Opportunity": {
			"doctype": "Supplier Quotation",
			"field_map": {
				"name": "opportunity"
			}
		},
		"Opportunity Item": {
			"doctype": "Supplier Quotation Item",
			"field_map": {
				"uom": "stock_uom"
			}
		}
	}, target_doc)

	return doclist


def get_active_vehicle_quotation(opportunity, include_draft=False):
	filters = {
		"opportunity": opportunity,
		"status": ("not in", ['Lost', 'Closed'])
	}

	if include_draft:
		filters["docstatus"] = ["<", 2]
	else:
		filters["docstatus"] = 1

	return frappe.db.get_value("Vehicle Quotation", filters)


def get_vehicle_booking_order(opportunity, include_draft=False):
	filters = {
		"opportunity": opportunity,
	}

	if include_draft:
		filters["docstatus"] = ["<", 2]
	else:
		filters["docstatus"] = 1

	return frappe.db.get_value("Vehicle Booking Order", filters)


@frappe.whitelist()
def set_multiple_status(names, status):
	names = json.loads(names)
	for name in names:
		opp = frappe.get_doc("Opportunity", name)
		opp.status = status
		opp.save()


def auto_close_opportunity():
	""" auto close the `Replied` Opportunities after 7 days """
	auto_close_after_days = frappe.db.get_single_value("CRM Settings", "close_opportunity_after_days")
	if auto_close_after_days < 1:
		return

	opportunities = frappe.db.sql("""
		select name from tabOpportunity
		where status='Replied' and modified<DATE_SUB(CURDATE(), INTERVAL %s DAY)
	""", (auto_close_after_days), as_dict=True)

	for opportunity in opportunities:
		doc = frappe.get_doc("Opportunity", opportunity.get("name"))
		doc.set_status(status="Closed")


@frappe.whitelist()
def make_opportunity_from_communication(communication, company, ignore_communication_links=False):
	from erpnext.crm.doctype.lead.lead import make_lead_from_communication
	doc = frappe.get_doc("Communication", communication)

	lead = doc.reference_name if doc.reference_doctype == "Lead" else None
	if not lead:
		lead = make_lead_from_communication(communication, ignore_communication_links=True)

	opportunity_from = "Lead"

	opportunity = frappe.get_doc({
		"doctype": "Opportunity",
		"company": company,
		"opportunity_from": opportunity_from,
		"party_name": lead
	}).insert(ignore_permissions=True)

	link_communication_to_document(doc, "Opportunity", opportunity.name, ignore_communication_links)

	return opportunity.name


def get_customer_from_opportunity(source):
	if source and source.get('party_name'):
		if source.get('opportunity_from') == 'Lead':
			customer = get_customer_from_lead(source.get('party_name'), throw=True)
			return frappe.get_cached_doc('Customer', customer)

		elif source.get('opportunity_from') == 'Customer':
			return frappe.get_cached_doc('Customer', source.get('party_name'))


@frappe.whitelist()
def submit_communication(name, contact_date, remarks, submit_follow_up=False):
	if not remarks:
		frappe.throw(_('Remarks are mandatory for Communication'))

	if not frappe.db.exists('Opportunity', name):
		frappe.throw(_("Opportunity does not exist"))

	opp = frappe.get_doc('Opportunity', name)

	comm = frappe.new_doc("Communication")
	comm.reference_doctype = opp.doctype
	comm.reference_name = opp.name
	comm.reference_owner = opp.owner

	comm.sender = frappe.session.user
	comm.sent_or_received = 'Received'
	comm.subject = "Opportunity Communication"
	comm.content = remarks
	comm.communication_type = "Feedback"

	comm.append("timeline_links", {
		"link_doctype": opp.opportunity_from,
		"link_name": opp.party_name,
	})

	comm.insert(ignore_permissions=True)

	if cint(submit_follow_up):
		follow_up = [f for f in opp.contact_schedule if not f.contact_date]
		if follow_up:
			follow_up[0].contact_date = getdate(contact_date)

		opp.save()


@frappe.whitelist()
def get_events(start, end, filters=None):
	from frappe.desk.calendar import get_event_conditions
	conditions = get_event_conditions("Opportunity", filters)

	data = frappe.db.sql("""
		select
			`tabOpportunity`.name, `tabOpportunity`.customer_name, `tabOpportunity`.status,
			`tabLead Follow Up`.schedule_date
		from
			`tabOpportunity`
		inner join
			`tabLead Follow Up` on `tabOpportunity`.name = `tabLead Follow Up`.parent
		where
			ifnull(`tabLead Follow Up`.schedule_date, '0000-00-00') != '0000-00-00'
			and `tabLead Follow Up`.schedule_date between %(start)s and %(end)s
			and `tabLead Follow Up`.parenttype = 'Opportunity'
			{conditions}
		""".format(conditions=conditions), {
			"start": start,
			"end": end
		}, as_dict=True, update={"allDay": 1})

	return data
