# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

BOM_FIELDS = [
	"company",
	"rm_cost_as_per",
	"project",
	"currency",
	"conversion_rate",
	"buying_price_list",
]


class BOMConfigurator(Document):
	def before_save(self):
		self.set_is_expandable()

	def before_submit(self):
		self.validate_fields()

	@frappe.whitelist()
	def add_boms(self):
		self.submit()

	def set_is_expandable(self):
		fg_items = [row.fg_item for row in self.items]
		for row in self.items:
			row.is_expandable = 0
			if row.item_code in fg_items:
				row.is_expandable = 1

	def validate_fields(self):
		fields = {
			"items": "Items",
		}

		for field, label in fields.items():
			if not self.get(field):
				frappe.throw(_("Please set {0} in BOM Configurator {1}").format(label, self.name))

	def on_submit(self):
		self.create_boms()

	def create_boms(self):
		production_item_wise_rm = frappe._dict({})
		for row in self.items:
			row.bom_no = ""
			if row.fg_item not in production_item_wise_rm:
				production_item_wise_rm.setdefault(row.fg_item, frappe._dict({"items": [], "bom_no": ""}))

			rm_item = production_item_wise_rm[row.fg_item]["items"]
			rm_item.append(row)

		for row in self.items[::-1]:
			if row.fg_item in production_item_wise_rm:
				if production_item_wise_rm.get(row.fg_item).bom_no:
					continue

				self.create_bom(row, production_item_wise_rm)

		frappe.msgprint(_("BOMs created successfully"))

	def create_bom(self, row, production_item_wise_rm):
		production_item_wise_rm

		bom = frappe.new_doc("BOM")
		bom.update(
			{
				"item": row.fg_item,
				"bom_type": "Production",
				"quantity": row.qty,
				"allow_alternative_item": 1,
				"bom_configurator": self.name,
			}
		)

		for field in BOM_FIELDS:
			if self.get(field):
				bom.set(field, self.get(field))

		for item in production_item_wise_rm[row.fg_item]["items"]:
			bom_no = ""
			if item.item_code in production_item_wise_rm:
				bom_no = production_item_wise_rm.get(item.item_code).bom_no
				item.do_not_explode = 0

			if not bom_no and not item.do_not_explode and not item.bom_no:
				bom_no = self.get_default_bom(item.item_code)

			bom.append(
				"items",
				{
					"item_code": item.item_code,
					"qty": item.qty,
					"uom": item.uom,
					"conversion_factor": item.conversion_factor,
					"stock_qty": item.stock_qty,
					"stock_uom": item.stock_uom,
					"do_not_explode": item.do_not_explode,
					"bom_no": bom_no,
					"allow_alternative_item": 1,
					"allow_scrap_items": 1,
					"include_item_in_manufacturing": 1,
				},
			)

		bom.save(ignore_permissions=True)
		bom.submit()

		production_item_wise_rm[row.fg_item].bom_no = bom.name

	@frappe.whitelist()
	def get_default_bom(self, item_code) -> str:
		return frappe.get_cached_value("Item", item_code, "default_bom")


@frappe.whitelist()
def get_children(**kwargs):
	if isinstance(kwargs, str):
		kwargs = frappe.parse_json(kwargs)

	if isinstance(kwargs, dict):
		kwargs = frappe._dict(kwargs)

	print(kwargs)

	fields = [
		"item_code as value",
		"is_expandable as expandable",
		"parent as parent_id",
		"qty",
		"idx",
		"'BOM Configurator Item' as doctype",
		"name",
		"uom",
	]

	query_filters = {
		"fg_item": kwargs.parent,
		"parent": kwargs.parent_id,
	}

	if kwargs.name:
		query_filters["name"] = kwargs.name

	data = frappe.get_all(
		"BOM Configurator Item", fields=fields, filters=query_filters, order_by="idx", debug=1
	)

	frappe.errprint(data)
	return data


@frappe.whitelist()
def add_item(**kwargs):
	if isinstance(kwargs, str):
		kwargs = frappe.parse_json(kwargs)

	if isinstance(kwargs, dict):
		kwargs = frappe._dict(kwargs)

	doc = frappe.get_doc("BOM Configurator", kwargs.parent)
	doc.append("items", kwargs)
	doc.save()


@frappe.whitelist()
def add_sub_assembly(**kwargs):
	if isinstance(kwargs, str):
		kwargs = frappe.parse_json(kwargs)

	if isinstance(kwargs, dict):
		kwargs = frappe._dict(kwargs)

	doc = frappe.get_doc("BOM Configurator", kwargs.parent)
	bom_item = frappe.parse_json(kwargs.bom_item)

	if not kwargs.convert_to_sub_assembly:
		item_info = get_item_details(bom_item.item_code)
		doc.append(
			"items",
			{
				"item_code": bom_item.item_code,
				"qty": bom_item.qty,
				"uom": item_info.stock_uom,
				"fg_item": kwargs.fg_item,
				"conversion_factor": 1,
				"stock_qty": bom_item.qty,
				"do_not_explode": 1,
				"stock_uom": item_info.stock_uom,
			},
		)

	for row in bom_item.get("items"):
		row = frappe._dict(row)
		item_info = get_item_details(row.item_code)
		doc.append(
			"items",
			{
				"item_code": row.item_code,
				"qty": row.qty,
				"fg_item": bom_item.item_code,
				"uom": item_info.stock_uom,
				"conversion_factor": 1,
				"do_not_explode": 1,
				"stock_qty": row.qty,
				"stock_uom": item_info.stock_uom,
			},
		)

	doc.save()
	return doc


def get_item_details(item_code):
	return frappe.get_cached_value(
		"Item", item_code, ["item_name", "description", "image", "stock_uom", "default_bom"], as_dict=1
	)


@frappe.whitelist()
def delete_node(**kwargs):
	if isinstance(kwargs, str):
		kwargs = frappe.parse_json(kwargs)

	if isinstance(kwargs, dict):
		kwargs = frappe._dict(kwargs)

	items = get_children(parent=kwargs.fg_item, parent_id=kwargs.parent)
	if kwargs.docname:
		frappe.delete_doc("BOM Configurator Item", kwargs.docname)

	for item in items:
		frappe.delete_doc("BOM Configurator Item", item.name)
		if item.expandable:
			delete_node(fg_item=item.value, parent=item.parent_id)


@frappe.whitelist()
def edit_qty(doctype, docname, qty):
	frappe.db.set_value(doctype, docname, "qty", qty)
