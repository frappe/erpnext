# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model import no_value_fields
from frappe.model.document import Document
from frappe.utils import cint, flt


class PackingSlip(Document):
	def validate(self):
		"""
		* Validate existence of submitted Delivery Note
		* Case nos do not overlap
		* Check if packed qty doesn't exceed actual qty of delivery note

		It is necessary to validate case nos before checking quantity
		"""
		self.validate_delivery_note()
		self.validate_items_mandatory()
		self.validate_case_nos()
		self.validate_qty()

		from erpnext.utilities.transaction_base import validate_uom_is_integer

		validate_uom_is_integer(self, "stock_uom", "qty")
		validate_uom_is_integer(self, "weight_uom", "net_weight")

		self.set_missing_values()

	def validate_delivery_note(self):
		"""
		Validates if delivery note has status as draft
		"""
		if cint(frappe.db.get_value("Delivery Note", self.delivery_note, "docstatus")) != 0:
			frappe.throw(_("Delivery Note {0} must not be submitted").format(self.delivery_note))

	def validate_items_mandatory(self):
		rows = [d.item_code for d in self.get("items")]
		if not rows:
			frappe.msgprint(_("No Items to pack"), raise_exception=1)

	def validate_case_nos(self):
		"""
		Validate if case nos overlap. If they do, recommend next case no.
		"""
		if not cint(self.from_case_no):
			frappe.msgprint(_("Please specify a valid 'From Case No.'"), raise_exception=1)
		elif not self.to_case_no:
			self.to_case_no = self.from_case_no
		elif cint(self.from_case_no) > cint(self.to_case_no):
			frappe.msgprint(_("'To Case No.' cannot be less than 'From Case No.'"), raise_exception=1)

		res = frappe.db.sql(
			"""SELECT name FROM `tabPacking Slip`
			WHERE delivery_note = %(delivery_note)s AND docstatus = 1 AND
			((from_case_no BETWEEN %(from_case_no)s AND %(to_case_no)s)
			OR (to_case_no BETWEEN %(from_case_no)s AND %(to_case_no)s)
			OR (%(from_case_no)s BETWEEN from_case_no AND to_case_no))
			""",
			{
				"delivery_note": self.delivery_note,
				"from_case_no": self.from_case_no,
				"to_case_no": self.to_case_no,
			},
		)

		if res:
			frappe.throw(
				_("""Case No(s) already in use. Try from Case No {0}""").format(self.get_recommended_case_no())
			)

	def validate_qty(self):
		"""Check packed qty across packing slips and delivery note"""
		# Get Delivery Note Items, Item Quantity Dict and No. of Cases for this Packing slip
		dn_details, ps_item_qty, no_of_cases = self.get_details_for_packing()

		for item in dn_details:
			new_packed_qty = (flt(ps_item_qty[item["item_code"]]) * no_of_cases) + flt(item["packed_qty"])
			if new_packed_qty > flt(item["qty"]) and no_of_cases:
				self.recommend_new_qty(item, ps_item_qty, no_of_cases)

	def set_missing_values(self):
		if not self.from_case_no:
			self.from_case_no = self.get_recommended_case_no()

		for item in self.items:
			weight_per_unit, weight_uom = frappe.db.get_value(
				"Item", item.item_code, ["weight_per_unit", "weight_uom"]
			)

			if weight_per_unit and not item.net_weight:
				item.net_weight = weight_per_unit
			if weight_uom and not item.weight_uom:
				item.weight_uom = weight_uom

	def get_details_for_packing(self):
		"""
		Returns
		* 'Delivery Note Items' query result as a list of dict
		* Item Quantity dict of current packing slip doc
		* No. of Cases of this packing slip
		"""

		rows = [d.item_code for d in self.get("items")]

		# also pick custom fields from delivery note
		custom_fields = ", ".join(
			"dni.`{0}`".format(d.fieldname)
			for d in frappe.get_meta("Delivery Note Item").get_custom_fields()
			if d.fieldtype not in no_value_fields
		)

		if custom_fields:
			custom_fields = ", " + custom_fields

		condition = ""
		if rows:
			condition = " and item_code in (%s)" % (", ".join(["%s"] * len(rows)))

		# gets item code, qty per item code, latest packed qty per item code and stock uom
		res = frappe.db.sql(
			"""select item_code, sum(qty) as qty,
			(select sum(psi.qty * (abs(ps.to_case_no - ps.from_case_no) + 1))
				from `tabPacking Slip` ps, `tabPacking Slip Item` psi
				where ps.name = psi.parent and ps.docstatus = 1
				and ps.delivery_note = dni.parent and psi.item_code=dni.item_code) as packed_qty,
			stock_uom, item_name, description, dni.batch_no {custom_fields}
			from `tabDelivery Note Item` dni
			where parent=%s {condition}
			group by item_code""".format(
				condition=condition, custom_fields=custom_fields
			),
			tuple([self.delivery_note] + rows),
			as_dict=1,
		)

		ps_item_qty = dict([[d.item_code, d.qty] for d in self.get("items")])
		no_of_cases = cint(self.to_case_no) - cint(self.from_case_no) + 1

		return res, ps_item_qty, no_of_cases

	def recommend_new_qty(self, item, ps_item_qty, no_of_cases):
		"""
		Recommend a new quantity and raise a validation exception
		"""
		item["recommended_qty"] = (flt(item["qty"]) - flt(item["packed_qty"])) / no_of_cases
		item["specified_qty"] = flt(ps_item_qty[item["item_code"]])
		if not item["packed_qty"]:
			item["packed_qty"] = 0

		frappe.throw(
			_("Quantity for Item {0} must be less than {1}").format(
				item.get("item_code"), item.get("recommended_qty")
			)
		)

	def get_recommended_case_no(self):
		"""Returns the next case no. for a new packing slip for a delivery note"""

		return (
			cint(
				frappe.db.get_value(
					"Packing Slip", {"delivery_note": self.delivery_note, "docstatus": 1}, ["max(to_case_no)"]
				)
			)
			+ 1
		)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def item_details(doctype, txt, searchfield, start, page_len, filters):
	from erpnext.controllers.queries import get_match_cond

	return frappe.db.sql(
		"""select name, item_name, description from `tabItem`
				where name in ( select item_code FROM `tabDelivery Note Item`
	 						where parent= %s)
	 			and %s like "%s" %s
	 			limit  %s offset %s """
		% ("%s", searchfield, "%s", get_match_cond(doctype), "%s", "%s"),
		((filters or {}).get("delivery_note"), "%%%s%%" % txt, page_len, start),
	)
