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
from webnotes import msgprint, _
from webnotes.utils import load_json, cstr, flt, now_datetime
from webnotes.model.doc import addchild

from controllers.status_updater import StatusUpdater

class TransactionBase(StatusUpdater):
	def get_default_address_and_contact(self, party_field, party_name=None):
		"""get a dict of default field values of address and contact for a given party type
			party_type can be one of: customer, supplier"""
		if not party_name:
			party_name = self.doc.fields.get(party_field)
		
		return get_default_address_and_contact(party_field, party_name,
			fetch_shipping_address=True if self.meta.get_field("shipping_address_name") else False)
			
	def get_customer_defaults(self):
		out = self.get_default_address_and_contact("customer")

		customer = webnotes.doc("Customer", self.doc.customer)
		for f in ['customer_name', 'customer_group', 'territory']:
			out[f] = customer.fields.get(f)
		
		# fields prepended with default in Customer doctype
		for f in ['sales_partner', 'commission_rate', 'currency', 'price_list']:
			out[f] = customer.fields.get("default_" + f)
			
		return out
				
	def set_customer_defaults(self):
		"""
			For a customer:
			1. Sets default address and contact
			2. Sets values like Territory, Customer Group, etc.
			3. Clears existing Sales Team and fetches the one mentioned in Customer
		"""
		customer_defaults = self.get_customer_defaults()
		
		# hack! TODO - add shipping_address_field in Delivery Note
		if self.doc.doctype == "Delivery Note":
			customer_defaults["customer_address"] = customer_defaults["shipping_address_name"]
			customer_defaults["address_display"] = customer_defaults["shipping_address"]
			
		customer_defaults["price_list"] = customer_defaults["price_list"] or \
			webnotes.conn.get_value("Customer Group", self.doc.customer_group, "default_price_list") or \
			self.doc.price_list
			
		self.doc.fields.update(customer_defaults)
		
		if self.meta.get_field("sales_team"):
			self.set_sales_team_for_customer()
			
	def set_sales_team_for_customer(self):
		from webnotes.model import default_fields
		
		# clear table
		self.doclist = self.doc.clear_table(self.doclist, "sales_team")

		sales_team = webnotes.conn.sql("""select * from `tabSales Team`
			where parenttype="Customer" and parent=%s""", self.doc.customer, as_dict=True)
		for i, sales_person in enumerate(sales_team):
			# remove default fields
			for fieldname in default_fields:
				if fieldname in sales_person:
					del sales_person[fieldname]
			
			sales_person.update({
				"doctype": "Sales Team",
				"parentfield": "sales_team",
				"idx": i+1
			})
			
			# add child
			self.doclist.append(sales_person)
	
	def get_lead_defaults(self):
		out = self.get_default_address_and_contact("lead")
		
		lead = webnotes.conn.get_value("Lead", self.doc.lead, 
			["territory", "company_name", "lead_name"], as_dict=True) or {}

		out["territory"] = lead.get("territory")
		out["customer_name"] = lead.get("company_name") or lead.get("lead_name")

		return out
		
	def set_lead_defaults(self):
		self.doc.fields.update(self.get_lead_defaults())
			
	
	# Get Customer Address
	# -----------------------
	def get_customer_address(self, args):
		args = load_json(args)		
		address_text, address_name = self.get_address_text(address_name=args['address'])
		ret = {
			'customer_address' : address_name,
			'address_display' : address_text,
		}
		
		ret.update(self.get_contact_text(contact_name=args['contact']))
		
		return ret	
			
	# Get Address Text
	# -----------------------
	def get_address_text(self, customer=None, address_name=None, supplier=None, is_shipping_address=None):
		if customer:
			cond = customer and 'customer="%s"' % customer or 'name="%s"' % address_name
		elif supplier:
			cond = supplier and 'supplier="%s"' % supplier or 'name="%s"' % address_name	
		else:
			cond = 'name="%s"' % address_name	

		if is_shipping_address:
			details = webnotes.conn.sql("select name, address_line1, address_line2, city, country, pincode, state, phone, fax from `tabAddress` where %s and docstatus != 2 order by is_shipping_address desc, is_primary_address desc limit 1" % cond, as_dict = 1)
		else:
			details = webnotes.conn.sql("select name, address_line1, address_line2, city, country, pincode, state, phone, fax from `tabAddress` where %s and docstatus != 2 order by is_primary_address desc limit 1" % cond, as_dict = 1)
		
		address_display = ""
		
		if details:
			address_display = get_address_display(details[0])			

		address_name = details and details[0]['name'] or ''
		
		return address_display, address_name

	# Get Contact Text
	# -----------------------
	def get_contact_text(self, customer=None, contact_name=None, supplier=None):
		if customer:
			cond = customer and 'customer="%s"' % customer or 'name="%s"' % contact_name
		elif supplier:
			cond = supplier and 'supplier="%s"' % supplier or 'name="%s"' % contact_name
		else:
			cond = 'name="%s"' % contact_name			
			
		details = webnotes.conn.sql("select name, first_name, last_name, email_id, phone, mobile_no, department, designation from `tabContact` where %s and docstatus != 2 order by is_primary_contact desc limit 1" % cond, as_dict = 1)

		extract = lambda x: details and details[0] and details[0].get(x,'') or ''
		contact_fields = [('','first_name'),(' ','last_name')]
		contact_display = ''.join([a[0]+cstr(extract(a[1])) for a in contact_fields if extract(a[1])])
		if contact_display.startswith('\n'): contact_display = contact_display[1:]
		
		return {
			"contact_display": contact_display,
			"contact_person": details and details[0]["name"] or "",
			"contact_email": details and details[0]["email_id"] or "",
			"contact_mobile": details and details[0]["mobile_no"] or "",
			"contact_designation": details and details[0]["designation"] or "",
			"contact_department": details and details[0]["department"] or "",
		}
		
	# TODO deprecate this - used only in sales_order.js
	def get_shipping_address(self, name):
		details = webnotes.conn.sql("select name, address_line1, address_line2, city, country, pincode, state, phone from `tabAddress` where customer = '%s' and docstatus != 2 order by is_shipping_address desc, is_primary_address desc limit 1" %(name), as_dict = 1)
		
		address_display = ""
		if details:
			address_display = get_address_display(details[0])
		
		ret = {
			'shipping_address_name' : details and details[0]['name'] or '',
			'shipping_address' : address_display
		}
		return ret
		
	# Get Supplier Default Primary Address - first load
	# -----------------------
	def get_default_supplier_address(self, args):
		if isinstance(args, basestring):
			args = load_json(args)
		address_text, address_name = self.get_address_text(supplier=args['supplier'])
		ret = {
			'supplier_address' : address_name,
			'address_display' : address_text,
		}
		ret.update(self.get_contact_text(supplier=args['supplier']))
		ret.update(self.get_supplier_details(args['supplier']))
		return ret
		
	# Get Supplier Address
	# -----------------------
	def get_supplier_address(self, args):
		args = load_json(args)
		address_text, address_name = self.get_address_text(address_name=args['address'])
		ret = {
			'supplier_address' : address_name,
			'address_display' : address_text,
		}
		ret.update(self.get_contact_text(contact_name=args['contact']))
		return ret
	
	# Get Supplier Details
	# -----------------------
	def get_supplier_details(self, name):
		supplier_details = webnotes.conn.sql("""\
			select supplier_name, default_currency
			from `tabSupplier`
			where name = %s and docstatus < 2""", name, as_dict=1)
		if supplier_details:
			return {
				'supplier_name': (supplier_details[0]['supplier_name']
					or self.doc.fields.get('supplier_name')),
				'currency': (supplier_details[0]['default_currency']
					or self.doc.fields.get('currency')),
			}
		else:
			return {}
		
	# Get Sales Person Details of Customer
	# ------------------------------------
	def get_sales_person(self, name):			
		self.doclist = self.doc.clear_table(self.doclist,'sales_team')
		idx = 0
		for d in webnotes.conn.sql("select sales_person, allocated_percentage, allocated_amount, incentives from `tabSales Team` where parent = '%s'" % name):
			ch = addchild(self.doc, 'sales_team', 'Sales Team', self.doclist)
			ch.sales_person = d and cstr(d[0]) or ''
			ch.allocated_percentage = d and flt(d[1]) or 0
			ch.allocated_amount = d and flt(d[2]) or 0
			ch.incentives = d and flt(d[3]) or 0
			ch.idx = idx
			idx += 1

	def load_notification_message(self):
		dt = self.doc.doctype.lower().replace(" ", "_")
		if int(webnotes.conn.get_value("Notification Control", None, dt) or 0):
			self.doc.fields["__notification_message"] = \
				webnotes.conn.get_value("Notification Control", None, dt + "_message")
				
	def add_communication_list(self):
		# remove communications if present
		self.doclist = webnotes.doclist(self.doclist).get({
			"doctype": ["!=", "Communcation"]})
		
		comm_list = webnotes.conn.sql("""select * from tabCommunication 
			where %s=%s order by modified desc limit 20""" \
			% (self.doc.doctype.replace(" ", "_").lower(), "%s"),
			self.doc.name, as_dict=1, update={"doctype":"Communication"})
		
		self.doclist.extend(webnotes.doclist([webnotes.doc(fielddata=d) \
			for d in comm_list]))
			
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
			where ref_type=%s and ref_name=%s""", (self.doc.doctype, self.doc.name)))
			
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
			
	def validate_with_previous_doc(self, source_dt, ref):
		for key, val in ref.items():
			ref_doc = {}
			for d in self.doclist.get({"doctype": source_dt}):
				if d.fields[val["ref_dn_field"]]:
					ref_doc.setdefault(key, d.fields[val["ref_dn_field"]])

			if val.get("is_child_table"):
				self.compare_values(ref_doc, val["compare_fields"], d)
			else:
				self.compare_values(ref_doc, val["compare_fields"])
	
	def compare_values(self, ref_doc, fields, doc=None):
		for ref_doctype, ref_docname in ref_doc.items():
			prevdoc_values = webnotes.conn.get_value(ref_doctype, ref_docname, 
				[d[0] for d in fields], as_dict=1)
			
			for field, condition in fields:
				self.validate_value(field, condition, prevdoc_values[field], doc)

def get_default_address_and_contact(party_field, party_name, fetch_shipping_address=False):
	out = {}
	
	# get addresses
	billing_address = get_address_dict(party_field, party_name)
	if billing_address:
		out[party_field + "_address"] = billing_address["name"]
		out["address_display"] = get_address_display(billing_address)
	else:
		out[party_field + "_address"] = out["address_display"] = None
	
	if fetch_shipping_address:
		shipping_address = get_address_dict(party_field, party_name, is_shipping_address=True)
		if shipping_address:
			out["shipping_address_name"] = shipping_address["name"]
			out["shipping_address"] = get_address_display(shipping_address)
		else:
			out["shipping_address_name"] = out["shipping_address"] = None
	
	# get contact
	if party_field == "lead":
		out["customer_address"] = out.get("lead_address")
		out.update(map_lead_fields(party_name))
	else:
		out.update(map_contact_fields(party_field, party_name))
	
	return out

def get_address_dict(party_field, party_name, is_shipping_address=None):
	order_by = "is_shipping_address desc, is_primary_address desc, name asc" if \
		is_shipping_address else "is_primary_address desc, name asc"

	address = webnotes.conn.sql("""select * from `tabAddress` where `%s`=%s order by %s
		limit 1""" % (party_field, "%s", order_by), party_name, as_dict=True,
		update={"doctype": "Address"})
	
	return address[0] if address else None
			
def get_address_display(address_dict):
	def _prepare_for_display(a_dict, sequence):
		display = ""
		for separator, fieldname in sequence:
			if a_dict.get(fieldname):
				display += separator + a_dict.get(fieldname)
			
		return display.strip()
	
	meta = webnotes.get_doctype("Address")
	address_sequence = (("", "address_line1"), ("\n", "address_line2"), ("\n", "city"),
		("\n", "state"), ("\n" + meta.get_label("pincode") + ": ", "pincode"), ("\n", "country"),
		("\n" + meta.get_label("phone") + ": ", "phone"), ("\n" + meta.get_label("fax") + ": ", "fax"))
	
	return _prepare_for_display(address_dict, address_sequence)
	
def map_lead_fields(party_name):
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

def map_contact_fields(party_field, party_name):
	out = {}
	for fieldname in ["contact_person", "contact_display", "contact_email",
		"contact_mobile", "contact_phone", "contact_designation", "contact_department"]:
			out[fieldname] = None
	
	contact = webnotes.conn.sql("""select * from `tabContact` where `%s`=%s
		order by is_primary_contact desc, name asc limit 1""" % (party_field, "%s"), 
		(party_name,), as_dict=True)
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
	
def validate_conversion_rate(currency, conversion_rate, conversion_rate_label, company):
	"""common validation for currency and price list currency"""
	if conversion_rate == 0:
		msgprint(conversion_rate_label + _(' cannot be 0'), raise_exception=True)
	
	company_currency = webnotes.conn.get_value("Company", company, "default_currency")
	
	# parenthesis for 'OR' are necessary as we want it to evaluate as 
	# mandatory valid condition and (1st optional valid condition 
	# 	or 2nd optional valid condition)
	valid_conversion_rate = (conversion_rate and 
		((currency == company_currency and conversion_rate == 1.00)
			or (currency != company_currency and conversion_rate != 1.00)))

	if not valid_conversion_rate:
		msgprint(_('Please enter valid ') + conversion_rate_label + (': ') 
			+ ("1 %s = [?] %s" % (currency, company_currency)),
			raise_exception=True)
			
def validate_item_fetch(args, item):
	from stock.utils import validate_end_of_life
	validate_end_of_life(item.name, item.end_of_life)
	
	# validate company
	if not args.company:
		msgprint(_("Please specify Company"), raise_exception=True)
	
def validate_currency(args, item, meta=None):
	from webnotes.model.meta import get_field_precision
	if not meta:
		meta = webnotes.get_doctype(args.doctype)
		
	# validate conversion rate
	if meta.get_field("currency"):
		validate_conversion_rate(args.currency, args.conversion_rate, 
			meta.get_label("conversion_rate"), args.company)
		
		# round it
		args.conversion_rate = flt(args.conversion_rate, 
			get_field_precision(meta.get_field("conversion_rate"), 
				webnotes._dict({"fields": args})))
	
	# validate price list conversion rate
	if meta.get_field("price_list_currency") and args.price_list_name and \
		args.price_list_currency:
		validate_conversion_rate(args.price_list_currency, args.plc_conversion_rate, 
			meta.get_label("plc_conversion_rate"), args.company)
		
		# round it
		args.plc_conversion_rate = flt(args.plc_conversion_rate, 
			get_field_precision(meta.get_field("plc_conversion_rate"), 
				webnotes._dict({"fields": args})))
	
def delete_events(ref_type, ref_name):
	webnotes.delete_doc("Event", webnotes.conn.sql_list("""select name from `tabEvent` 
		where ref_type=%s and ref_name=%s""", (ref_type, ref_name)), for_reload=True)
