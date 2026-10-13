# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, nowdate


class Shareholder(Document):
	def validate(self):
		if not self.is_new():
			frappe.db.get_value("Shareholder", self.name, "name", for_update=True)
		self.validate_joint_holding()
		self.validate_nominees()
		self.set_current_holdings()

	def set_current_holdings(self):
		"""Keep the child table as a rebuildable projection of the share ledger."""
		if self.is_new():
			self.set("current_holdings", [])
			return
		self.set("current_holdings", get_current_holding_rows(self.name))

	def validate_joint_holding(self):
		if self.shareholder_type != "Individual":
			self.is_joint_holding = 0
			self.set("joint_holders", [])
			return

		if not self.is_joint_holding:
			self.set("joint_holders", [])
			return

		# A joint holding represents two or more people under one Shareholder ID.
		if len(self.joint_holders) < 2:
			frappe.throw(_("A joint holding must contain at least two joint holders."))

		seen_tax_ids = set()
		for holder in self.joint_holders:
			normalized_tax_id = (holder.tax_id or "").strip().casefold()
			if normalized_tax_id in seen_tax_ids:
				frappe.throw(_("Joint holder tax IDs must be unique within a Shareholder."))
			seen_tax_ids.add(normalized_tax_id)

		# Tax identity belongs to each child row for a joint holding.
		self.tax_id_type = None
		self.tax_id = None
		self.tax_id_country = None

	def validate_nominees(self):
		if not self.nominees:
			return

		total_allocation = 0
		for nominee in self.nominees:
			allocation = flt(nominee.allocation_percentage)
			if allocation <= 0 or allocation > 100:
				frappe.throw(_("Nominee allocation must be greater than 0 and no more than 100%."))
			total_allocation += allocation

		if flt(total_allocation, 6) != 100:
			frappe.throw(_("Nominee allocations must total 100%."))


def get_current_holding_rows(shareholder: str):
	"""Use locking reads so the stored projection includes the latest committed movements."""
	entry = frappe.qb.DocType("Share Ledger Entry")
	folio = frappe.qb.DocType("Share Folio")
	movements = (
		frappe.qb.from_(entry)
		.join(folio)
		.on(folio.name == entry.share_folio)
		.select(
			entry.company,
			entry.share_class,
			entry.share_folio,
			folio.folio_number,
			entry.quantity_change,
			entry.face_value_per_share,
			entry.currency,
		)
		.where((folio.shareholder == shareholder) & (entry.posting_date <= nowdate()))
		.for_update()
	).run(as_dict=True)
	positions = {}
	for movement in movements:
		key = (movement.company, movement.share_class, movement.share_folio, movement.currency)
		if key not in positions:
			positions[key] = {
				"company": movement.company,
				"share_class": movement.share_class,
				"share_folio": movement.share_folio,
				"folio_number": movement.folio_number,
				"currency": movement.currency,
				"quantity": 0,
				"total_face_value": 0,
				"unknown_quantity": 0,
			}
		position = positions[key]
		position["quantity"] += movement.quantity_change
		if not movement.face_value_per_share:
			position["unknown_quantity"] += movement.quantity_change
		position["total_face_value"] += movement.quantity_change * flt(movement.face_value_per_share)
	rows = []
	for position in positions.values():
		if not position["quantity"]:
			continue
		if position.pop("unknown_quantity"):
			position["total_face_value"] = None
		position["face_value_per_share"] = (
			position["total_face_value"] / position["quantity"]
			if position["total_face_value"] is not None
			else None
		)
		rows.append(position)
	return sorted(rows, key=lambda row: (row["company"], row["share_class"], row["share_folio"]))


def rebuild_current_holdings(shareholder: str):
	"""Replace only the derived child rows; never save unrelated Shareholder fields."""
	if not isinstance(shareholder, str) or not shareholder:
		frappe.throw(_("A Shareholder is required to rebuild holdings."))
	frappe.db.get_value("Shareholder", shareholder, "name", for_update=True)
	frappe.db.set_value("Shareholder", shareholder, "modified", now_datetime(), update_modified=False)
	rows = get_current_holding_rows(shareholder)
	frappe.db.delete(
		"Shareholder Current Balance",
		{"parent": shareholder, "parenttype": "Shareholder", "parentfield": "current_holdings"},
	)
	for index, row in enumerate(rows, start=1):
		frappe.get_doc(
			{
				"doctype": "Shareholder Current Balance",
				"parent": shareholder,
				"parenttype": "Shareholder",
				"parentfield": "current_holdings",
				"idx": index,
				**row,
			}
		).db_insert()
