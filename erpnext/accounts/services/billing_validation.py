# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

"""Billing amount validation helpers (overbilling checks)."""

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import cint, flt, fmt_money


class BillingValidationService:
	def __init__(self, doc):
		self.doc = doc

	def validate_multiple_billing(self, ref_dt: str, item_ref_dn: str, based_on: str) -> None:
		from erpnext.controllers.status_updater import get_allowance_for

		ref_wise_billed_amount = self.get_reference_wise_billed_amt(ref_dt, item_ref_dn, based_on)
		if not ref_wise_billed_amount:
			return

		total_overbilled_amt = 0.0
		overbilled_items = []
		precision = self.doc.precision(based_on, "items")
		precision_allowance = 1 / (10**precision)

		role_allowed_to_overbill = frappe.get_single_value("Accounts Settings", "role_allowed_to_over_bill")
		is_overbilling_allowed = role_allowed_to_overbill in frappe.get_roles()

		for row in ref_wise_billed_amount.values():
			total_billed_amt = row.billed_amt
			allowance = get_allowance_for(row.item_code, {}, None, None, "amount")[0]
			max_allowed_amt = flt(row.ref_amt * (100 + allowance) / 100)

			if total_billed_amt < 0 and max_allowed_amt < 0:
				total_billed_amt, max_allowed_amt = abs(total_billed_amt), abs(max_allowed_amt)

			overbill_amt = total_billed_amt - max_allowed_amt
			row["max_allowed_amt"] = max_allowed_amt
			total_overbilled_amt += overbill_amt

			if overbill_amt > precision_allowance and not is_overbilling_allowed:
				if self.doc.doctype != "Purchase Invoice" or not cint(
					frappe.db.get_single_value(
						"Buying Settings", "bill_for_rejected_quantity_in_purchase_invoice"
					)
				):
					overbilled_items.append(row)

		if overbilled_items:
			self.throw_overbill_exception(overbilled_items, precision)

		if is_overbilling_allowed and total_overbilled_amt > 0.1:
			frappe.msgprint(
				_("Overbilling of {} ignored because you have {} role.").format(
					total_overbilled_amt, role_allowed_to_overbill
				),
				indicator="orange",
				alert=True,
			)

	def get_reference_wise_billed_amt(self, ref_dt: str, item_ref_dn: str, based_on: str) -> dict | None:
		"""Return sum of billed amounts per reference row, including previously submitted invoices."""
		reference_names = [d.get(item_ref_dn) for d in self.doc.items if d.get(item_ref_dn)]
		if not reference_names:
			return

		precision = self.doc.precision(based_on, "items")
		reference_details = self.get_billing_reference_details(reference_names, ref_dt + " Item", based_on)
		already_billed = self.get_already_billed_amount(reference_names, item_ref_dn, based_on)

		ref_wise_billed_amount = {}
		for item in self.doc.items:
			key = item.get(item_ref_dn)
			if not key:
				continue

			ref_amt = flt(reference_details.get(key), precision)
			current_amount = flt(item.get(based_on), precision)

			if not ref_amt:
				if current_amount:
					frappe.msgprint(
						_(
							"System will not check over billing since amount for Item {0} in {1} is zero"
						).format(item.item_code, ref_dt),
						title=_("Warning"),
						indicator="orange",
					)
				continue

			ref_wise_billed_amount.setdefault(
				key,
				frappe._dict(item_code=item.item_code, billed_amt=0.0, ref_amt=ref_amt, rows=[]),
			)
			ref_wise_billed_amount[key]["rows"].append(item.idx)
			ref_wise_billed_amount[key]["ref_amt"] = ref_amt
			ref_wise_billed_amount[key]["billed_amt"] += current_amount
			if key in already_billed:
				ref_wise_billed_amount[key]["billed_amt"] += flt(already_billed.pop(key, 0), precision)

		return ref_wise_billed_amount

	def get_billing_reference_details(
		self, reference_names: list, reference_doctype: str, based_on: str
	) -> frappe._dict:
		return frappe._dict(
			frappe.get_all(
				reference_doctype,
				filters={"name": ("in", reference_names)},
				fields=["name", based_on],
				as_list=1,
			)
		)

	def get_already_billed_amount(
		self, reference_names: list, item_ref_dn: str, based_on: str
	) -> frappe._dict:
		item_doctype = frappe.qb.DocType(self.doc.items[0].doctype)
		based_on_field = frappe.qb.Field(based_on)
		join_field = frappe.qb.Field(item_ref_dn)

		return frappe._dict(
			(
				frappe.qb.from_(item_doctype)
				.select(join_field, Sum(based_on_field))
				.where(join_field.isin(reference_names))
				.where((item_doctype.docstatus == 1) & (item_doctype.parent != self.doc.name))
				.groupby(join_field)
			).run()
		)

	def throw_overbill_exception(self, overbilled_items: list, precision: int) -> None:
		message = (
			_("<p>Cannot overbill for the following Items:</p>")
			+ "<ul>"
			+ "".join(
				_("<li>Item {0} in row(s) {1} billed more than {2}</li>").format(
					frappe.bold(item.item_code),
					", ".join(str(x) for x in item.rows),
					frappe.bold(
						fmt_money(item.max_allowed_amt, precision=precision, currency=self.doc.currency)
					),
				)
				for item in overbilled_items
			)
			+ "</ul>"
		)
		message += _("<p>To allow over-billing, please set allowance in Accounts Settings.</p>")
		frappe.throw(_(message))
