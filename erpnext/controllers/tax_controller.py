import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import cint, flt


class TaxController(Document):
	def validate_taxes_and_charges(self):
		if self.charge_type in ["Actual", "On Net Total", "On Paid Amount"] and self.row_id:
			frappe.throw(
				_("Can refer row only if the charge type is 'On Previous Row Amount' or 'Previous Row Total'")
			)
		elif self.charge_type in ["On Previous Row Amount", "On Previous Row Total"]:
			if cint(self.idx) == 1:
				frappe.throw(
					_(
						"Cannot select charge type as 'On Previous Row Amount' or 'On Previous Row Total' for first row"
					)
				)
			elif not self.row_id:
				frappe.throw(
					_("Please specify a valid Row ID for row {0} in table {1}").format(self.idx, _(self.doctype))
				)
			elif self.row_id and cint(self.row_id) >= cint(self.idx):
				frappe.throw(
					_("Cannot refer row number greater than or equal to current row number for this Charge type")
				)

		if self.charge_type == "Actual":
			self.rate = None

	def validate_inclusive_tax(self, all_taxes: list["TaxController"]):
		def _on_previous_row_error(row_range):
			frappe.throw(
				_("To include tax in row {0} in Item rate, taxes in rows {1} must also be included").format(
					self.idx, row_range
				)
			)

		if not self.assume_gross_rate:
			return

		if self.charge_type == "Actual":
			# inclusive tax cannot be of type Actual
			frappe.throw(
				_("Charge of type 'Actual' in row {0} cannot be included in Item Rate or Paid Amount").format(
					self.idx
				)
			)
		elif self.charge_type == "On Previous Row Amount" and not cint(
			all_taxes[self.previous_row_id].assume_gross_rate
		):
			# referred row should also be inclusive
			_on_previous_row_error(self.row_id)
		elif self.charge_type == "On Previous Row Total" and not all(
			t.assume_gross_rate for t in all_taxes[: self.previous_row_id]
		):
			# all rows about the referred tax should be inclusive
			_on_previous_row_error("1 - %d" % (self.row_id,))
		elif self.get("category") == "Valuation":
			frappe.throw(_("Valuation type charges can not be marked as Inclusive"))

	def validate_cost_center(self, company: str):
		if not self.cost_center:
			return

		cost_center_company = frappe.get_cached_value("Cost Center", self.cost_center, "company")
		if cost_center_company != company:
			frappe.throw(
				_("Row {0}: Cost Center {1} does not belong to Company {2}").format(
					self.idx, frappe.bold(self.cost_center), frappe.bold(company)
				),
				title=_("Invalid Cost Center"),
			)

	def validate_account_head(self, company: str):
		if frappe.get_cached_value("Account", self.account_head, "company") != company:
			frappe.throw(
				_("Row {0}: Taxes and Charges Account {1} does not belong to Company {2}").format(
					self.idx, frappe.bold(self.account_head), frappe.bold(company)
				),
				title=_("Invalid Account"),
			)

	def get_tax_rate(self, item_tax_map: dict[str, float]):
		return (
			flt(item_tax_map.get(self.account_head), self.precision("rate"))
			if self.account_head in item_tax_map
			else self.rate
		)

	def set_current_tax_fraction(self, all_taxes: list["TaxController"], tax_rate: float):
		"""
		Get tax fraction for calculating tax exclusive amount
		from tax inclusive amount
		"""
		current_tax_fraction = 0

		if self.assume_gross_rate:
			if self.charge_type in ("On Net Total", "On Paid Amount"):
				current_tax_fraction = tax_rate / 100.0

			elif self.charge_type == "On Previous Row Amount":
				current_tax_fraction = (tax_rate / 100.0) * all_taxes[
					self.previous_row_id
				].tax_fraction_for_current_item

			elif self.charge_type == "On Previous Row Total":
				current_tax_fraction = (tax_rate / 100.0) * all_taxes[
					self.previous_row_id
				].grand_total_fraction_for_current_item

		if getattr(self, "add_deduct_tax", None) == "Deduct":
			current_tax_fraction *= -1.0

		self.current_tax_fraction = current_tax_fraction

	def get_inclusive_tax_amount_per_qty(self, tax_rate: float):
		inclusive_tax_amount_per_qty = 0
		if self.assume_gross_rate and self.charge_type == "On Item Quantity":
			inclusive_tax_amount_per_qty = flt(tax_rate)

		if getattr(self, "add_deduct_tax", None) == "Deduct":
			inclusive_tax_amount_per_qty *= -1.0

		return inclusive_tax_amount_per_qty

	def round_off_totals(self):
		if self.account_head in frappe.flags.round_off_applicable_accounts:
			self.tax_amount = round(self.tax_amount, 0)
			self.tax_amount_after_discount_amount = round(self.tax_amount_after_discount_amount, 0)

		self.tax_amount = flt(self.tax_amount, self.precision("tax_amount"))
		self.tax_amount_after_discount_amount = flt(
			self.tax_amount_after_discount_amount, self.precision("tax_amount")
		)

	def round_off_base_values(self):
		if self.account_head not in frappe.flags.round_off_applicable_accounts:
			return

		self.base_tax_amount = round(self.base_tax_amount, 0)
		self.base_tax_amount_after_discount_amount = round(self.base_tax_amount_after_discount_amount, 0)

	def get_item_wise_tax(self) -> dict[str, list[float]]:
		return json.loads(self.item_wise_tax_detail) if self.item_wise_tax_detail else {}

	def add_item_wise_tax(self, item: str, rate: float, amount: float) -> None:
		item_wise_tax = self.get_item_wise_tax()
		if item_wise_tax.get(item):
			amount += item_wise_tax[item][1]
		item_wise_tax[item] = [rate, amount]
		self.item_wise_tax_detail = json.dumps(item_wise_tax, separators=(",", ":"))

	@property
	def previous_row_id(self):
		return cint(self.row_id) - 1

	@property
	def assume_gross_rate(self):
		return cint(
			getattr(
				self,
				"included_in_paid_amount" if self.parenttype == "Payment Entry" else "included_in_print_rate",
				None,
			)
		)
