# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import msgprint, _
from webnotes.utils import cstr, flt, now_datetime, cint

from erpnext.controllers.status_updater import StatusUpdater


class TransactionBase(StatusUpdater):
	def set_contact_fields(self):
		party_type, party_name = self.get_party_type_and_name()
		
		if party_type == "Lead":
			contact_dict = map_lead_contact_details(party_name)
		else:
			contact_dict = map_party_contact_details(self.doc.contact_person, party_type, party_name)
			
		for fieldname, value in contact_dict.items():
			if self.meta.get_field(fieldname):
				self.doc.fields[fieldname] = value
		
	def get_party_type_and_name(self):
		if not hasattr(self, "_party_type_and_name"):
			for party_type in ("Lead", "Customer", "Supplier"):
				party_field = party_type.lower()
				if self.meta.get_field(party_field) and self.doc.fields.get(party_field):
					self._party_type_and_name = (party_type, self.doc.fields.get(party_field))
					break

		return self._party_type_and_name
				
	def get_lead_defaults(self):
		out = self.get_default_address_and_contact("lead")
		
		lead = webnotes.conn.get_value("Lead", self.doc.lead, 
			["territory", "company_name", "lead_name"], as_dict=True) or {}

		out["territory"] = lead.get("territory")
		out["customer_name"] = lead.get("company_name") or lead.get("lead_name")

		return out
		
	def set_lead_defaults(self):
		self.doc.fields.update(self.get_lead_defaults())

	def load_notification_message(self):
		dt = self.doc.doctype.lower().replace(" ", "_")
		if int(webnotes.conn.get_value("Notification Control", None, dt) or 0):
			self.doc.fields["__notification_message"] = \
				webnotes.conn.get_value("Notification Control", None, dt + "_message")
							
	def validate_posting_time(self):
		if not self.doc.posting_time:
			self.doc.posting_time = now_datetime().strftime('%H:%M:%S')
			
	def add_calendar_event(self, opts, force=False):
		if self.doc.contact_by != cstr(self._prev.contact_by) or \
				self.doc.contact_date != cstr(self._prev.contact_date) or force:
			
			self.delete_events()
			self._add_calendar_event(opts)
			
	def delete_events(self):
		webnotes.delete_doc("Event", webnotes.conn.sql_list("""select name from `tabEvent` 
			where ref_type=%s and ref_name=%s""", (self.doc.doctype, self.doc.name)), 
			ignore_permissions=True)
			
	def _add_calendar_event(self, opts):
		opts = webnotes._dict(opts)
		
		if self.doc.contact_date:
			event_doclist = [{
				"doctype": "Event",
				"owner": opts.owner or self.doc.owner,
				"subject": opts.subject,
				"description": opts.description,
				"starts_on": self.doc.contact_date + " 10:00:00",
				"event_type": "Private",
				"ref_type": self.doc.doctype,
				"ref_name": self.doc.name
			}]
			
			if webnotes.conn.exists("Profile", self.doc.contact_by):
				event_doclist.append({
					"doctype": "Event User",
					"parentfield": "event_individuals",
					"person": self.doc.contact_by
				})
			
			webnotes.bean(event_doclist).insert()
			
	def validate_uom_is_integer(self, uom_field, qty_fields):
		validate_uom_is_integer(self.doclist, uom_field, qty_fields)
			
	def validate_with_previous_doc(self, source_dt, ref):
		for key, val in ref.items():
			is_child = val.get("is_child_table")
			ref_doc = {}
			item_ref_dn = []
			for d in self.doclist.get({"doctype": source_dt}):
				ref_dn = d.fields.get(val["ref_dn_field"])
				if ref_dn:
					if is_child:
						self.compare_values({key: [ref_dn]}, val["compare_fields"], d)
						if ref_dn not in item_ref_dn:
							item_ref_dn.append(ref_dn)
						elif not val.get("allow_duplicate_prev_row_id"):
							webnotes.msgprint(_("Row ") + cstr(d.idx + 1) + 
								_(": Duplicate row from same ") + key, raise_exception=1)
					elif ref_dn:
						ref_doc.setdefault(key, [])
						if ref_dn not in ref_doc[key]:
							ref_doc[key].append(ref_dn)
			if ref_doc:
				self.compare_values(ref_doc, val["compare_fields"])
	
	def compare_values(self, ref_doc, fields, doc=None):
		for ref_doctype, ref_dn_list in ref_doc.items():
			for ref_docname in ref_dn_list:
				prevdoc_values = webnotes.conn.get_value(ref_doctype, ref_docname, 
					[d[0] for d in fields], as_dict=1)

				for field, condition in fields:
					if prevdoc_values[field] is not None:
						self.validate_value(field, condition, prevdoc_values[field], doc)

def get_default_contact(party_field, party_name):
	contact = webnotes.conn.sql("""select name from `tabContact` where `%s`=%s
		order by is_primary_contact desc, name asc limit 1""" % (party_field, "%s"), 
		(party_name,))
		
	return contact[0][0] if contact else None
		
def map_lead_contact_details(party_name):
	out = {}
	for fieldname in ["contact_display", "contact_email", "contact_mobile", "contact_phone"]:
		out[fieldname] = None
	
	lead = webnotes.conn.sql("""select * from `tabLead` where name=%s""", party_name, as_dict=True)
	if lead:
		lead = lead[0]
		out.update({
			"contact_display": lead.get("lead_name"),
			"contact_email": lead.get("email_id"),
			"contact_mobile": lead.get("mobile_no"),
			"contact_phone": lead.get("phone"),
		})

	return out

def map_party_contact_details(contact_name=None, party_field=None, party_name=None):
	out = {}
	for fieldname in ["contact_person", "contact_display", "contact_email",
		"contact_mobile", "contact_phone", "contact_designation", "contact_department"]:
			out[fieldname] = None
			
	if not contact_name and party_field:
		contact_name = get_default_contact(party_field, party_name)
	
	if contact_name:
		contact = webnotes.conn.sql("""select * from `tabContact` where name=%s""", 
			contact_name, as_dict=True)

		if contact:
			contact = contact[0]
			out.update({
				"contact_person": contact.get("name"),
				"contact_display": " ".join(filter(None, 
					[contact.get("first_name"), contact.get("last_name")])),
				"contact_email": contact.get("email_id"),
				"contact_mobile": contact.get("mobile_no"),
				"contact_phone": contact.get("phone"),
				"contact_designation": contact.get("designation"),
				"contact_department": contact.get("department")
			})

	return out
	
def get_address_territory(address_doc):
	territory = None
	for fieldname in ("city", "state", "country"):
		value = address_doc.fields.get(fieldname)
		if value:
			territory = webnotes.conn.get_value("Territory", value.strip())
			if territory:
				break
	
	return territory
	
def delete_events(ref_type, ref_name):
	webnotes.delete_doc("Event", webnotes.conn.sql_list("""select name from `tabEvent` 
		where ref_type=%s and ref_name=%s""", (ref_type, ref_name)), for_reload=True)

class UOMMustBeIntegerError(webnotes.ValidationError): pass

def validate_uom_is_integer(doclist, uom_field, qty_fields):
	if isinstance(qty_fields, basestring):
		qty_fields = [qty_fields]
	
	integer_uoms = filter(lambda uom: webnotes.conn.get_value("UOM", uom, 
		"must_be_whole_number") or None, doclist.get_distinct_values(uom_field))
		
	if not integer_uoms:
		return

	for d in doclist:
		if d.fields.get(uom_field) in integer_uoms:
			for f in qty_fields:
				if d.fields.get(f):
					if cint(d.fields[f])!=d.fields[f]:
						webnotes.msgprint(_("For UOM") + " '" + d.fields[uom_field] \
							+ "': " + _("Quantity cannot be a fraction.") \
							+ " " + _("In Row") + ": " + str(d.idx),
							raise_exception=UOMMustBeIntegerError)
