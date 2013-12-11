# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes import msgprint, _
from webnotes.utils import load_json, cstr, flt, now_datetime, cint
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
			
	def set_address_fields(self):
		party_type, party_name = self.get_party_type_and_name()
		
		if party_type in ("Customer", "Lead"):
			if self.doc.customer_address:
				self.doc.address_display = get_address_display(self.doc.customer_address)
				
			if self.doc.shipping_address_name:
				self.doc.shipping_address = get_address_display(self.doc.shipping_address_name)
			
		elif self.doc.supplier_address:
			self.doc.address_display = get_address_display(self.doc.supplier_address)
		
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
			
	def get_customer_defaults(self):
		if not self.doc.customer: return {}
		
		out = self.get_default_address_and_contact("customer")

		customer = webnotes.doc("Customer", self.doc.customer)
		for f in ['customer_name', 'customer_group', 'territory']:
			out[f] = customer.fields.get(f)
		
		# fields prepended with default in Customer doctype
		for f in ['sales_partner', 'commission_rate', 'currency', 'price_list']:
			if customer.fields.get("default_" + f):
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
					
		customer_defaults["selling_price_list"] = customer_defaults.get("price_list") or \
			webnotes.conn.get_value("Customer Group", self.doc.customer_group, "default_price_list") or \
			self.doc.selling_price_list
			
		for fieldname, val in customer_defaults.items():
			if self.meta.get_field(fieldname):
				self.doc.fields[fieldname] = val
			
		if self.meta.get_field("sales_team") and self.doc.customer:
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
			
	def get_supplier_defaults(self):
		out = self.get_default_address_and_contact("supplier")

		supplier = webnotes.doc("Supplier", self.doc.supplier)
		out["supplier_name"] = supplier.supplier_name
		if supplier.default_currency:
			out["currency"] = supplier.default_currency
		if supplier.default_price_list:
			out["buying_price_list"] = supplier.default_price_list
		
		return out
		
	def set_supplier_defaults(self):
		for fieldname, val in self.get_supplier_defaults().items():
			if self.meta.get_field(fieldname):
				self.doc.fields[fieldname] = val
				
	def get_lead_defaults(self):
		out = self.get_default_address_and_contact("lead")
		
		lead = webnotes.conn.get_value("Lead", self.doc.lead, 
			["territory", "company_name", "lead_name"], as_dict=True) or {}

		out["territory"] = lead.get("territory")
		out["customer_name"] = lead.get("company_name") or lead.get("lead_name")

		return out
		
	def set_lead_defaults(self):
		self.doc.fields.update(self.get_lead_defaults())
	
	def get_customer_address(self, args):
		args = load_json(args)
		ret = {
			'customer_address' : args["address"],
			'address_display' : get_address_display(args["address"]),
		}
		if args.get('contact'):
			ret.update(map_party_contact_details(args['contact']))
		
		return ret
		
	def set_customer_address(self, args):
		self.doc.fields.update(self.get_customer_address(args))
		
	# TODO deprecate this - used only in sales_order.js
	def get_shipping_address(self, name):
		shipping_address = get_default_address("customer", name, is_shipping_address=True)
		return {
			'shipping_address_name' : shipping_address,
			'shipping_address' : get_address_display(shipping_address) if shipping_address else None
		}
		
	# Get Supplier Default Primary Address - first load
	# -----------------------
	def get_default_supplier_address(self, args):
		if isinstance(args, basestring):
			args = load_json(args)
			
		address_name = get_default_address("supplier", args["supplier"])
		ret = {
			'supplier_address' : address_name,
			'address_display' : get_address_display(address_name),
		}
		ret.update(map_party_contact_details(None, "supplier", args["supplier"]))
		ret.update(self.get_supplier_details(args['supplier']))
		return ret
		
	# Get Supplier Address
	# -----------------------
	def get_supplier_address(self, args):
		args = load_json(args)
		ret = {
			'supplier_address' : args['address'],
			'address_display' : get_address_display(args["address"]),
		}
		ret.update(map_party_contact_details(contact_name=args['contact']))
		return ret
		
	def set_supplier_address(self, args):
		self.doc.fields.update(self.get_supplier_address(args))
	
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

def get_default_address_and_contact(party_field, party_name, fetch_shipping_address=False):
	out = {}
	
	# get addresses
	billing_address = get_default_address(party_field, party_name)
	if billing_address:
		out[party_field + "_address"] = billing_address
		out["address_display"] = get_address_display(billing_address)
	else:
		out[party_field + "_address"] = out["address_display"] = None
	
	if fetch_shipping_address:
		shipping_address = get_default_address(party_field, party_name, is_shipping_address=True)
		if shipping_address:
			out["shipping_address_name"] = shipping_address
			out["shipping_address"] = get_address_display(shipping_address)
		else:
			out["shipping_address_name"] = out["shipping_address"] = None
	
	# get contact
	if party_field == "lead":
		out["customer_address"] = out.get("lead_address")
		out.update(map_lead_contact_details(party_name))
	else:
		out.update(map_party_contact_details(None, party_field, party_name))
	
	return out
	
def get_default_address(party_field, party_name, is_shipping_address=False):
	if is_shipping_address:
		order_by = "is_shipping_address desc, is_primary_address desc, name asc"
	else:
		order_by = "is_primary_address desc, name asc"
		
	address = webnotes.conn.sql("""select name from `tabAddress` where `%s`=%s order by %s
		limit 1""" % (party_field, "%s", order_by), party_name)
	
	return address[0][0] if address else None

def get_default_contact(party_field, party_name):
	contact = webnotes.conn.sql("""select name from `tabContact` where `%s`=%s
		order by is_primary_contact desc, name asc limit 1""" % (party_field, "%s"), 
		(party_name,))
		
	return contact[0][0] if contact else None
	
def get_address_display(address_dict):
	if not isinstance(address_dict, dict):
		address_dict = webnotes.conn.get_value("Address", address_dict, "*", as_dict=True) or {}
	
	meta = webnotes.get_doctype("Address")
	sequence = (("", "address_line1"), ("\n", "address_line2"), ("\n", "city"),
		("\n", "state"), ("\n" + meta.get_label("pincode") + ": ", "pincode"), ("\n", "country"),
		("\n" + meta.get_label("phone") + ": ", "phone"), ("\n" + meta.get_label("fax") + ": ", "fax"))
	
	display = ""
	for separator, fieldname in sequence:
		if address_dict.get(fieldname):
			display += separator + address_dict.get(fieldname)
		
	return display.strip()
	
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
	
def validate_conversion_rate(currency, conversion_rate, conversion_rate_label, company):
	"""common validation for currency and price list currency"""

	company_currency = webnotes.conn.get_value("Company", company, "default_currency")

	if not conversion_rate:
		msgprint(_('%(conversion_rate_label)s is mandatory. Maybe Currency Exchange \
			record is not created for %(from_currency)s to %(to_currency)s') % {
				"conversion_rate_label": conversion_rate_label,
				"from_currency": currency,
				"to_currency": company_currency
		}, raise_exception=True)
			
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
	if meta.get_field("price_list_currency") and (args.selling_price_list or args.buying_price_list) \
		and args.price_list_currency:
		validate_conversion_rate(args.price_list_currency, args.plc_conversion_rate, 
			meta.get_label("plc_conversion_rate"), args.company)
		
		# round it
		args.plc_conversion_rate = flt(args.plc_conversion_rate, 
			get_field_precision(meta.get_field("plc_conversion_rate"), 
				webnotes._dict({"fields": args})))
	
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
