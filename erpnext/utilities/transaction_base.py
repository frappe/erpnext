# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr, now_datetime, cint, flt
import frappe.share

from erpnext.controllers.status_updater import StatusUpdater


class TransactionBase(StatusUpdater):
	def load_notification_message(self):
		dt = self.doctype.lower().replace(" ", "_")
		if int(frappe.db.get_value("Notification Control", None, dt) or 0):
			self.set("__notification_message",
				frappe.db.get_value("Notification Control", None, dt + "_message"))

	def validate_posting_time(self):
		if not self.posting_time:
			self.posting_time = now_datetime().strftime('%H:%M:%S')

	def add_calendar_event(self, opts, force=False):
		if cstr(self.contact_by) != cstr(self._prev.contact_by) or \
				cstr(self.contact_date) != cstr(self._prev.contact_date) or force:

			self.delete_events()
			self._add_calendar_event(opts)

	def delete_events(self):
		events = frappe.db.sql_list("""select name from `tabEvent`
			where ref_type=%s and ref_name=%s""", (self.doctype, self.name))
		if events:
			frappe.db.sql("delete from `tabEvent` where name in (%s)"
				.format(", ".join(['%s']*len(events))), tuple(events))
				
			frappe.db.sql("delete from `tabEvent Role` where parent in (%s)"
				.format(", ".join(['%s']*len(events))), tuple(events))

	def _add_calendar_event(self, opts):
		opts = frappe._dict(opts)

		if self.contact_date:
			event = frappe.get_doc({
				"doctype": "Event",
				"owner": opts.owner or self.owner,
				"subject": opts.subject,
				"description": opts.description,
				"starts_on": self.contact_date + " 10:00:00",
				"event_type": "Private",
				"ref_type": self.doctype,
				"ref_name": self.name
			})

			event.insert(ignore_permissions=True)

			if frappe.db.exists("User", self.contact_by):
				frappe.share.add("Event", event.name, self.contact_by, 
					flags={"ignore_share_permission": True})

	def validate_uom_is_integer(self, uom_field, qty_fields):
		validate_uom_is_integer(self, uom_field, qty_fields)

	def validate_with_previous_doc(self, ref):
		for key, val in ref.items():
			is_child = val.get("is_child_table")
			ref_doc = {}
			item_ref_dn = []
			for d in self.get_all_children(self.doctype + " Item"):
				ref_dn = d.get(val["ref_dn_field"])
				if ref_dn:
					if is_child:
						self.compare_values({key: [ref_dn]}, val["compare_fields"], d)
						if ref_dn not in item_ref_dn:
							item_ref_dn.append(ref_dn)
						elif not val.get("allow_duplicate_prev_row_id"):
							frappe.throw(_("Duplicate row {0} with same {1}").format(d.idx, key))
					elif ref_dn:
						ref_doc.setdefault(key, [])
						if ref_dn not in ref_doc[key]:
							ref_doc[key].append(ref_dn)
			if ref_doc:
				self.compare_values(ref_doc, val["compare_fields"])

	def compare_values(self, ref_doc, fields, doc=None):
		for reference_doctype, ref_dn_list in ref_doc.items():
			for reference_name in ref_dn_list:
				prevdoc_values = frappe.db.get_value(reference_doctype, reference_name,
					[d[0] for d in fields], as_dict=1)

				for field, condition in fields:
					if prevdoc_values[field] is not None:
						self.validate_value(field, condition, prevdoc_values[field], doc)
						
						
	def validate_rate_with_reference_doc(self, ref_details):
		for ref_dt, ref_dn_field, ref_link_field in ref_details:
			for d in self.get("items"):
				if d.get(ref_link_field):
					ref_rate = frappe.db.get_value(ref_dt + " Item", d.get(ref_link_field), "rate")
					
					if abs(flt(d.rate - ref_rate, d.precision("rate"))) >= .01:
						frappe.throw(_("Row #{0}: Rate must be same as {1}: {2} ({3} / {4}) ")
							.format(d.idx, ref_dt, d.get(ref_dn_field), d.rate, ref_rate))


def delete_events(ref_type, ref_name):
	frappe.delete_doc("Event", frappe.db.sql_list("""select name from `tabEvent`
		where ref_type=%s and ref_name=%s""", (ref_type, ref_name)), for_reload=True)

class UOMMustBeIntegerError(frappe.ValidationError): pass

def validate_uom_is_integer(doc, uom_field, qty_fields, child_dt=None):
	if isinstance(qty_fields, basestring):
		qty_fields = [qty_fields]

	distinct_uoms = list(set([d.get(uom_field) for d in doc.get_all_children()]))
	integer_uoms = filter(lambda uom: frappe.db.get_value("UOM", uom,
		"must_be_whole_number") or None, distinct_uoms)

	if not integer_uoms:
		return

	for d in doc.get_all_children(parenttype=child_dt):
		if d.get(uom_field) in integer_uoms:
			for f in qty_fields:
				if d.get(f):
					if cint(d.get(f))!=d.get(f):
						frappe.throw(_("Quantity cannot be a fraction in row {0}").format(d.idx), UOMMustBeIntegerError)

def make_return_doc(doctype, source_name, target_doc=None):
	from frappe.model.mapper import get_mapped_doc
	def set_missing_values(source, target):
		doc = frappe.get_doc(target)
		doc.is_return = 1
		doc.return_against = source.name
		doc.ignore_pricing_rule = 1
		doc.run_method("calculate_taxes_and_totals")

	def update_item(source_doc, target_doc, source_parent):
		target_doc.qty = -1* source_doc.qty
		if doctype == "Purchase Receipt":
			target_doc.received_qty = -1* source_doc.qty
		elif doctype == "Purchase Invoice":
			target_doc.purchase_receipt = source_doc.purchase_receipt
			target_doc.pr_detail = source_doc.pr_detail

	doclist = get_mapped_doc(doctype, source_name,	{
		doctype: {
			"doctype": doctype,
			
			"validation": {
				"docstatus": ["=", 1],
			}
		},
		doctype +" Item": {
			"doctype": doctype + " Item",
			"postprocess": update_item
		},
	}, target_doc, set_missing_values)

	return doclist
