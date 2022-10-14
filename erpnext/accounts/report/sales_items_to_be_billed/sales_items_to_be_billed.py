# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.utils import flt, cint, cstr, getdate
from six import string_types


def execute(filters=None):
	return ItemsToBeBilled(filters).run("Customer")


class ItemsToBeBilled:
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or dict())
		if self.filters.from_date and self.filters.to_date and self.filters.from_date > self.filters.to_date:
			frappe.throw(_("Date Range is incorrect"))

	def run(self, party_type, claim_billing=False):
		self.filters.party_type = party_type
		self.filters.claim_billing = cint(self.filters.claim_billing or claim_billing)

		self.show_item_name = frappe.defaults.get_global_default('item_naming_by') != "Item Name"

		self.show_party_name = False
		if party_type == "Customer":
			self.show_party_name = frappe.defaults.get_global_default('cust_master_name') == "Naming Series"
		if party_type == "Supplier":
			self.show_party_name = frappe.defaults.get_global_default('supp_master_name') == "Naming Series"

		self.get_data()
		self.prepare_data()
		self.get_columns()
		return self.columns, self.data

	def get_data(self):
		order_doctype = "Sales Order" if self.filters.party_type == "Customer" else "Purchase Order"
		delivery_doctype = "Delivery Note" if self.filters.party_type == "Customer" else "Purchase Receipt"

		fieldnames = self.get_fieldnames()

		party_join = ""
		sales_person_join = ""
		sales_person_field = ""
		if self.filters.party_type == "Customer":
			party_join = "inner join `tabCustomer` cus on cus.name = o.customer"
			sales_person_field = ", GROUP_CONCAT(DISTINCT sp.sales_person SEPARATOR ', ') as sales_person"
			sales_person_join = "left join `tabSales Team` sp on sp.parent = o.name and sp.parenttype = {0}"
		elif self.filters.party_type == "Supplier":
			party_join = "inner join `tabSupplier` sup on sup.name = o.supplier"

		project_type_join = ""
		project_fields = ""
		if self.filters.claim_billing:
			project_type_join = "left join `tabProject` proj on proj.name = o.project"
			project_fields = ", proj.project_type, proj.project_date"

		common_fields = """
			o.name, o.company, o.creation, o.currency, o.project,
			o.{party_field} as party, o.{party_name_field} as party_name, i.claim_customer,
			i.item_code, i.item_name, i.warehouse, i.name as row_name,
			i.{qty_field} as qty, i.uom, i.stock_uom, i.alt_uom,
			i.conversion_factor, i.alt_uom_size,
			i.billed_qty, i.returned_qty, i.billed_amt,
			i.rate, i.amount, im.item_group, im.brand
			{sales_person_field} {project_fields}
		""".format(
			party_field=fieldnames.party,
			party_name_field=fieldnames.party_name,
			qty_field=fieldnames.qty,
			sales_person_field=sales_person_field,
			project_fields=project_fields
		)

		order_data = []
		if not self.filters.doctype or self.filters.doctype == order_doctype:
			conditions = self.get_conditions(order_doctype)

			order_data = frappe.db.sql("""
				SELECT '{doctype}' as doctype, o.transaction_date, {common_fields}
				FROM `tab{doctype}` o
				INNER JOIN `tab{doctype} Item` i ON i.parent = o.name
				INNER JOIN `tabItem` im on im.name = i.item_code
				{sales_person_join}
				{party_join}
				{project_type_join}
				WHERE
					o.docstatus = 1 AND o.status != 'Closed'
					AND (i.billed_qty + i.returned_qty) < i.qty
					AND (im.is_stock_item = 0 AND im.is_fixed_asset = 0)
					{conditions}
				GROUP BY o.name, i.name
			""".format(
				doctype=order_doctype,
				common_fields=common_fields,
				sales_person_join=sales_person_join.format(frappe.db.escape(order_doctype)),
				party_join=party_join,
				project_type_join=project_type_join,
				conditions=conditions,
			), self.filters, as_dict=1)

		delivery_data = []
		if not self.filters.doctype or self.filters.doctype == delivery_doctype:
			conditions = self.get_conditions(delivery_doctype)

			delivery_data = frappe.db.sql("""
				SELECT '{doctype}' as doctype, o.posting_date as transaction_date, {common_fields}
				FROM `tab{doctype}` o
				INNER JOIN `tab{doctype} Item` i ON i.parent = o.name
				INNER JOIN `tabItem` im on im.name = i.item_code
				{sales_person_join}
				{party_join}
				{project_type_join}
				WHERE
					o.docstatus = 1 AND o.status != 'Closed'
					AND (i.billed_qty + i.returned_qty) < i.qty
					AND (im.is_stock_item = 1 OR im.is_fixed_asset = 1 OR ifnull(i.{order_reference_field}, '') = '')
					{conditions}
				GROUP BY o.name, i.name
			""".format(
				doctype=delivery_doctype,
				common_fields=common_fields,
				order_reference_field=scrub(order_doctype),
				party_join=party_join,
				project_type_join=project_type_join,
				sales_person_join=sales_person_join.format(frappe.db.escape(delivery_doctype)),
				conditions=conditions,
			), self.filters, as_dict=1)

		data = order_data + delivery_data

		if self.filters.date_type == "Project Date":
			data = sorted(data, key=lambda d: (getdate(d.project_date), d.project))
		else:
			data = sorted(data, key=lambda d: (getdate(d.transaction_date), d.creation))

		self.data = data

	def get_fieldnames(self):
		fields = frappe._dict({})

		fields.party = scrub(self.filters.party_type)
		fields.party_name = fields.party + "_name"

		qty_field_filters = {
			"Stock Qty": "stock_qty",
			"Contents Qty": "alt_uom_qty",
			"Transaction Qty": "qty"
		}
		fields.qty = qty_field_filters.get(self.filters.qty_field) or "stock_qty"

		return fields

	def get_date_field(self, doctype):
		if self.filters.date_type == "Project Date":
			return "proj.project_date"
		else:
			if doctype in ["Sales Order", "Purchase Order"]:
				return "o.transaction_date"
			else:
				return "o.posting_date"

	def get_conditions(self, doctype):
		conditions = []

		if self.filters.company:
			conditions.append("o.company = %(company)s")

		if self.filters.name:
			conditions.append("o.name = %(name)s")

		if self.filters.transaction_type:
			conditions.append("o.transaction_type = %(transaction_type)s")

		if self.filters.customer:
			conditions.append("o.customer = %(customer)s")

		if self.filters.supplier:
			conditions.append("o.supplier = %(supplier)s")

		date_field = self.get_date_field(doctype)
		if self.filters.from_date:
			conditions.append("{} >= %(from_date)s".format(date_field))
		if self.filters.to_date:
			conditions.append("{} <= %(to_date)s".format(date_field))

		if self.filters.territory:
			lft, rgt = frappe.db.get_value("Territory", self.filters.territory, ["lft", "rgt"])
			conditions.append("""o.territory in (select name from `tabTerritory`
				where lft >= {0} and rgt <= {1})""".format(lft, rgt))

		if self.filters.claim_customer:
			conditions.append("i.claim_customer = %(claim_customer)s")

		if self.filters.claim_billing:
			conditions.append("ifnull(i.claim_customer, '') != ''")

		if self.filters.warehouse:
			lft, rgt = frappe.db.get_value("Warehouse", self.filters.warehouse, ["lft", "rgt"])
			conditions.append("""i.warehouse in (select name from `tabWarehouse`
				where lft >= {0} and rgt <= {1})""".format(lft, rgt))

		if self.filters.project:
			if isinstance(self.filters.project, string_types):
				self.filters.project = cstr(self.filters.get("project")).strip()
				self.filters.project = [d.strip() for d in self.filters.project.split(',') if d]

			if frappe.get_meta(doctype + " Item").has_field("project") and frappe.get_meta(doctype).has_field("project"):
				conditions.append("IF(i.project IS NULL or i.project = '', o.project, i.project) in %(project)s")
			elif frappe.get_meta(doctype + " Item").has_field("project"):
				conditions.append("i.project in %(project)s")
			elif frappe.get_meta(doctype).has_field("project"):
				conditions.append("o.project in %(project)s")

		if self.filters.brand:
			conditions.append("im.brand = %(brand)s")

		if self.filters.item_source:
			conditions.append("im.item_source = %(item_source)s")

		if self.filters.item_code:
			if frappe.db.get_value("Item", self.filters.item_code, 'has_variants'):
				conditions.append("im.variant_of = %(item_code)s")
			else:
				conditions.append("i.item_code = %(item_code)s")

		if self.filters.item_group:
			lft, rgt = frappe.db.get_value("Item Group", self.filters.item_group, ["lft", "rgt"])
			conditions.append("""im.item_group IN (SELECT name FROM `tabItem Group`
				WHERE lft >= {0} AND rgt <= {1})""".format(lft, rgt))

		if self.filters.customer_group:
			lft, rgt = frappe.db.get_value("Customer Group", self.filters.customer_group, ["lft", "rgt"])
			conditions.append("""cus.customer_group IN (SELECT name FROM `tabCustomer Group`
				WHERE lft >= {0} AND rgt <= {1})""".format(lft, rgt))

		if self.filters.supplier_group:
			lft, rgt = frappe.db.get_value("Supplier Group", self.filters.supplier_group, ["lft", "rgt"])
			conditions.append("""sup.supplier_group IN (SELECT name FROM `tabSupplier Group`
				WHERE lft >= {0} AND rgt <= {1})""".format(lft, rgt))

		if self.filters.sales_person:
			lft, rgt = frappe.db.get_value("Sales Person", self.filters.sales_person, ["lft", "rgt"])
			conditions.append("""sp.sales_person in (select name from `tabSales Person`
				where lft >= {0} and rgt <= {1})""".format(lft, rgt))

		if self.filters.project_type:
			conditions.append("proj.project_type = %(project_type)s")

		return "AND {}".format(" AND ".join(conditions)) if conditions else ""

	def prepare_data(self):
		for d in self.data:
			# Set UOM based on qty field
			if self.filters.qty_field == "Contents Qty":
				d.uom = d.alt_uom or d.stock_uom
				d.billed_qty = d.billed_qty * d.conversion_factor * d.alt_uom_size
				d.returned_qty = d.returned_qty * d.conversion_factor * d.alt_uom_size
			elif self.filters.qty_field == "Stock Qty":
				d.uom = d.stock_uom
				d.billed_qty = d.billed_qty * d.conversion_factor
				d.returned_qty = d.returned_qty * d.conversion_factor

			d['rate'] = d['amount'] / d['qty'] if d['qty'] else d['rate']
			d["remaining_qty"] = d["qty"] - d["billed_qty"] - d['returned_qty']

			d["remaining_amt"] = d["amount"] - d["billed_amt"]

			if d["amount"] >= 0:
				d["remaining_amt"] = max(0, d["remaining_amt"])
			else:
				d["remaining_amt"] = min(0, d["remaining_amt"])

			d["delay_days"] = max((getdate() - getdate(d["transaction_date"])).days, 0)

			d["disable_item_formatter"] = cint(self.show_item_name)
			d["disable_party_name_formatter"] = cint(self.show_party_name)

	def get_columns(self):
		columns = [
			{
				"label": _("Transaction Date"),
				"fieldname": "transaction_date",
				"fieldtype": "Date",
				"width": 80
			},
			{
				"label": _("Project Date"),
				"fieldname": "project_date",
				"fieldtype": "Date",
				"width": 80
			},
			{
				"label": _("Project Type"),
				"fieldname": "project_type",
				"fieldtype": "Link",
				"options": "Project Type",
				"width": 120
			},
			{
				"label": _("Document Type"),
				"fieldname": "doctype",
				"fieldtype": "Data",
				"width": 90 if self.filters.party_type == "Customer" else 110
			},
			{
				"label": _("Document"),
				"fieldname": "name",
				"fieldtype": "Dynamic Link",
				"options": "doctype",
				"width": 140
			},
			{
				"label": _("Project"),
				"fieldname": "project",
				"fieldtype": "Link",
				"options": "Project",
				"width": 100
			},
			{
				"label": _(self.filters.party_type),
				"fieldname": "party",
				"fieldtype": "Link",
				"options": self.filters.party_type,
				"width": 80 if self.show_party_name else 150
			},
			{
				"label": _(self.filters.party_type) + " Name",
				"fieldname": "party_name",
				"fieldtype": "Data",
				"width": 150
			},
			{
				"label": _("Item Code"),
				"fieldname": "item_code",
				"fieldtype": "Link",
				"options": "Item",
				"width": 100 if self.show_item_name else 150
			},
			{
				"label": _("Item Name"),
				"fieldname": "item_name",
				"fieldtype": "Data",
				"width": 150
			},
			{
				"label": _("UOM"),
				"fieldtype": "Link",
				"options": "UOM",
				"fieldname": "uom",
				"width": 50
			},
			{
				"label": _("Qty"),
				"fieldname": "qty",
				"fieldtype": "Float",
				"width": 80
			},
			{
				"label": _("Billed"),
				"fieldname": "billed_qty",
				"fieldtype": "Float",
				"width": 80
			},
			{
				"label": _("Returned"),
				"fieldname": "returned_qty",
				"fieldtype": "Float",
				"width": 80
			},
			{
				"label": _("Remaining"),
				"fieldname": "remaining_qty",
				"fieldtype": "Float",
				"width": 80
			},
			{
				"label": _("Amount"),
				"fieldname": "amount",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			},
			{
				"label": _("Billed Amount"),
				"fieldname": "billed_amt",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			},
			{
				"label": _("Remaining Amount"),
				"fieldname": "remaining_amt",
				"fieldtype": "Currency",
				"options": "currency",
				"width": 120
			},
			{
				"label": _("Sales Person"),
				"fieldtype": "Data",
				"fieldname": "sales_person",
				"width": 150
			},
			{
				"label": _("Delay Days"),
				"fieldname": "delay_days",
				"fieldtype": "Int",
				"width": 85
			},
			{
				"label": _("Item Group"),
				"fieldname": "item_group",
				"fieldtype": "Link",
				"options": "Item Group",
				"width": 90
			},
			{
				"label": _("Brand"),
				"fieldname": "brand",
				"fieldtype": "Link",
				"options": "Brand",
				"width": 60
			},
			{
				"label": _("Warehouse"),
				"fieldname": "warehouse",
				"fieldtype": "Link",
				"options": "Warehouse",
				"width": 90
			},
		]

		if not self.show_item_name:
			columns = [c for c in columns if c['fieldname'] != 'item_name']
		
		if not self.show_party_name:
			columns = [c for c in columns if c['fieldname'] != 'party_name']

		if self.filters.party_type != "Customer":
			columns = [c for c in columns if c['fieldname'] != 'sales_person']

		if self.filters.date_type == "Project Date":
			columns = [c for c in columns if c['fieldname'] != 'transaction_date']
		else:
			columns = [c for c in columns if c['fieldname'] != 'project_date']

		if not self.filters.claim_billing:
			columns = [c for c in columns if c['fieldname'] != 'project_type']

		self.columns = columns
