import frappe
from frappe import _
from frappe.query_builder.functions import Sum

from .base import BaseStockEntry
from .manufacturing import get_bom_items


class MaterialReceiptStockEntry(BaseStockEntry):
	def before_validate(self):
		self.set_default_warehouse()

	def validate(self):
		self.validate_warehouse()

	def set_default_warehouse(self):
		for row in self.doc.items:
			row.s_warehouse = None
			if not row.t_warehouse and self.doc.to_warehouse:
				row.t_warehouse = self.doc.to_warehouse

	def validate_warehouse(self):
		for row in self.doc.items:
			if not row.t_warehouse:
				frappe.throw(_("Target Warehouse is required for item {0}").format(row.item_code))


class BaseMaterialIssueStockEntry(BaseStockEntry):
	def set_default_warehouse(self):
		for row in self.doc.items:
			row.t_warehouse = None
			if not row.s_warehouse and self.doc.from_warehouse:
				row.s_warehouse = self.doc.from_warehouse

	def validate_warehouse(self):
		for row in self.doc.items:
			if not row.s_warehouse:
				frappe.throw(_("Source Warehouse is required for item {0}").format(row.item_code))


class MaterialIssueStockEntry(BaseMaterialIssueStockEntry):
	def before_validate(self):
		self.set_default_warehouse()

	def validate(self):
		self.validate_warehouse()

	def add_items(self):
		self.add_raw_materials_based_on_bom()

	def add_raw_materials_based_on_bom(self):
		bom_items = get_bom_items(self.doc.bom_no, self.doc.use_multi_level_bom)

		for row in bom_items:
			row.s_warehouse = self.doc.from_warehouse
			row.qty = row.qty * self.doc.fg_completed_qty
			if not row.uom:
				row.uom = row.stock_uom

			self.doc.append("items", row)


def get_consumed_items(work_order):
	"""Get all raw materials consumed through consumption entries for a work order."""
	parent = frappe.qb.DocType("Stock Entry")
	child = frappe.qb.DocType("Stock Entry Detail")

	return (
		frappe.qb.from_(parent)
		.join(child)
		.on(parent.name == child.parent)
		.select(
			child.item_code,
			Sum(child.qty).as_("qty"),
			child.original_item,
		)
		.where(
			(parent.docstatus == 1)
			& (parent.purpose == "Material Consumption for Manufacture")
			& (parent.work_order == work_order)
		)
		.groupby(child.item_code, child.original_item)
	).run(as_dict=True)
