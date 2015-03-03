# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr, now_datetime, cint
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
		if self.contact_by != cstr(self._prev.contact_by) or \
				self.contact_date != cstr(self._prev.contact_date) or force:

			self.delete_events()
			self._add_calendar_event(opts)

	def delete_events(self):
		frappe.delete_doc("Event", frappe.db.sql_list("""select name from `tabEvent`
			where ref_type=%s and ref_name=%s""", (self.doctype, self.name)),
			ignore_permissions=True)

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
				frappe.share.add("Event", event.name, self.contact_by)

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
		for ref_doctype, ref_dn_list in ref_doc.items():
			for ref_docname in ref_dn_list:
				prevdoc_values = frappe.db.get_value(ref_doctype, ref_docname,
					[d[0] for d in fields], as_dict=1)

				for field, condition in fields:
					if prevdoc_values[field] is not None:
						self.validate_value(field, condition, prevdoc_values[field], doc)


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
