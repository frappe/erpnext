# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub, unscrub
from frappe.utils import getdate, nowdate, flt, cint, cstr
from erpnext.accounts.report.item_wise_sales_register.item_wise_sales_register import get_tax_accounts
from erpnext.accounts.report.financial_statements import get_cost_centers_with_children
from frappe.desk.query_report import group_report_data
from erpnext import get_default_currency
from six import iteritems, string_types


class SalesPurchaseDetailsReport(object):
	def __init__(self, filters=None):
		self.filters = frappe._dict(filters or {})
		self.filters.from_date = getdate(self.filters.from_date or nowdate())
		self.filters.to_date = getdate(self.filters.to_date or nowdate())

		self.show_item_name = frappe.defaults.get_global_default('item_naming_by') != "Item Name"

		self.additional_customer_info = frappe._dict()

		self.date_field = 'transaction_date' \
			if self.filters.doctype in ['Sales Order', 'Purchase Order'] else 'posting_date'

		if self.filters.get('company'):
			self.company_currency = frappe.get_cached_value('Company', self.filters.get("company"), "default_currency")
		else:
			self.company_currency = get_default_currency()

		self.amount_fields = []
		self.rate_fields = []

		if cint(self.filters.show_basic_values):
			if cint(self.filters.show_discount_values):
				self.amount_fields += ['base_amount_before_discount', 'base_total_discount']
				self.rate_fields += [
					('base_discount_rate', 'base_total_discount', 'base_amount_before_discount', 100),
					('base_rate_before_discount', 'base_amount_before_discount')
				]
			self.amount_fields += ['base_amount']
			self.rate_fields += [('base_rate', 'base_amount')]

		if cint(self.filters.show_tax_exclusive_values):
			if cint(self.filters.show_discount_values):
				self.amount_fields += ['base_tax_exclusive_amount_before_discount', 'base_tax_exclusive_total_discount']
				self.rate_fields += [
					('base_tax_exclusive_discount_rate', 'base_tax_exclusive_total_discount', 'base_tax_exclusive_amount_before_discount', 100),
					('base_tax_exclusive_rate_before_discount', 'base_tax_exclusive_amount_before_discount')
				]
			self.amount_fields += ['base_tax_exclusive_amount']
			self.rate_fields += [('base_tax_exclusive_rate', 'base_tax_exclusive_amount')]

		self.amount_fields += ['base_net_amount']
		self.rate_fields += [('base_net_rate', 'base_net_amount')]

	def run(self, party_type):
		if self.filters.from_date > self.filters.to_date:
			frappe.throw(_("From Date must be before To Date"))

		if self.filters.get("cost_center") \
				and not frappe.get_meta(self.filters.doctype + " Item").has_field("cost_center")\
				and not frappe.get_meta(self.filters.doctype).has_field("cost_center"):
			frappe.throw(_("Cannot filter {0} by Cost Center").format(self.filters.doctype))

		self.filters.party_type = party_type

		self.show_party_name = False
		if self.filters.party_type == "Customer":
			if frappe.defaults.get_global_default('cust_master_name') == "Naming Series":
				self.show_party_name = True
		if self.filters.party_type == "Supplier":
			if frappe.defaults.get_global_default('supp_master_name') == "Naming Series":
				self.show_party_name = True

		self.get_entries()
		self.get_itemised_taxes()
		self.prepare_data()
		data = self.get_grouped_data()
		columns = self.get_columns()
		return columns, data

	def get_entries(self):
		party_field = scrub(self.filters.party_type)
		party_name_field = party_field + "_name"
		qty_field = self.get_qty_fieldname()

		sales_person_join = "left join `tabSales Team` sp on sp.parent = s.name and sp.parenttype = %(doctype)s" \
			if self.filters.party_type == "Customer" else ""
		sales_person_field = ", GROUP_CONCAT(DISTINCT sp.sales_person SEPARATOR ', ') as sales_person" if sales_person_join else ""
		contribution_field = ", sum(ifnull(sp.allocated_percentage, 100)) as allocated_percentage" if sales_person_join else ""

		bill_no_field = ", s.bill_no" if frappe.get_meta(self.filters.doctype).has_field('bill_no') else ""
		bill_date_field = ", s.bill_date" if frappe.get_meta(self.filters.doctype).has_field('bill_date') else ""

		party_join = ""
		if self.filters.party_type == "Customer":
			party_join = "inner join `tabCustomer` cus on cus.name = s.customer"
		elif self.filters.party_type == "Supplier":
			party_join = "inner join `tabSupplier` sup on sup.name = s.supplier"

		territory_field = ", s.territory" if self.filters.party_type == "Customer" else ""

		item_cost_center_field = ", i.cost_center as item_cost_center" if frappe.get_meta(self.filters.doctype + " Item").has_field("cost_center")\
			else ""
		parent_cost_center_field = ", s.cost_center as parent_cost_center" if frappe.get_meta(self.filters.doctype).has_field("cost_center")\
			else ""

		item_project_field = ", i.project as item_project" if frappe.get_meta(self.filters.doctype + " Item").has_field("project")\
			else ""
		parent_project_field = ", s.project as parent_project" if frappe.get_meta(self.filters.doctype).has_field("project")\
			else ""

		party_group_field = ", cus.customer_group as party_group, 'Customer Group' as party_group_dt" if self.filters.party_type == "Customer"\
			else ", sup.supplier_group as party_group, 'Supplier Group' as party_group_dt"

		is_opening_condition = "and s.is_opening != 'Yes'" if self.filters.doctype in ['Sales Invoice', 'Purchase Invoice']\
			else ""

		stin_field = ", s.stin" if self.filters.doctype == "Sales Invoice" else ""

		amount_fields = ", ".join(["i."+f for f in self.amount_fields])

		filter_conditions = self.get_conditions()

		self.entries = frappe.db.sql("""
			select
				s.name as parent, i.name, s.{date_field} as date,
				s.{party_field} as party, s.{party_name_field} as party_name,
				i.item_code, i.item_name,
				i.{qty_field} as qty,
				i.uom, i.stock_uom, i.alt_uom,
				im.brand, im.item_group,
				s.applies_to_item, s.applies_to_variant_of,
				{amount_fields} {party_group_field} {territory_field} {sales_person_field} {contribution_field}
				{item_cost_center_field} {parent_cost_center_field}
				{item_project_field} {parent_project_field}
				{stin_field} {bill_no_field} {bill_date_field}
			from `tab{doctype} Item` i
			inner join `tab{doctype}` s on i.parent = s.name
			left join `tabItem` im on im.name = i.item_code
			{party_join}
			{sales_person_join}
			where s.docstatus = 1
				and s.{date_field} between %(from_date)s and %(to_date)s
				{is_opening_condition} {filter_conditions}
			group by s.name, i.name
			order by s.{date_field}, s.{party_field}, s.name, i.item_code
		""".format(
			party_field=party_field,
			party_name_field=party_name_field,
			party_group_field=party_group_field,
			territory_field=territory_field,
			qty_field=qty_field,
			amount_fields=amount_fields,
			date_field=self.date_field,
			bill_no_field=bill_no_field,
			bill_date_field=bill_date_field,
			doctype=self.filters.doctype,
			stin_field=stin_field,
			sales_person_field=sales_person_field,
			contribution_field=contribution_field,
			sales_person_join=sales_person_join,
			item_cost_center_field=item_cost_center_field,
			parent_cost_center_field=parent_cost_center_field,
			item_project_field=item_project_field,
			parent_project_field=parent_project_field,
			party_join=party_join,
			is_opening_condition=is_opening_condition,
			filter_conditions=filter_conditions
		), self.filters, as_dict=1)

		if self.filters.party_type == "Customer" and "Group by Customer" in [self.filters.group_by_1, self.filters.group_by_2, self.filters.group_by_3]:
			additional_customer_info = frappe.db.sql("""
				select
					s.customer, GROUP_CONCAT(DISTINCT s.territory SEPARATOR ', ') as territory
					{sales_person_field}
				from `tab{doctype} Item` i
				inner join `tab{doctype}` s on i.parent = s.name
				left join `tabItem` im on im.name = i.item_code
				{party_join}
				{sales_person_join}
				where s.docstatus = 1
					and sp.parent = s.name and sp.parenttype = %(doctype)s
					and s.{date_field} between %(from_date)s and %(to_date)s
					{is_opening_condition} {filter_conditions}
				group by s.{party_field}
			""".format(
				party_field=party_field,
				date_field=self.date_field,
				doctype=self.filters.doctype,
				sales_person_field=sales_person_field,
				sales_person_join=sales_person_join,
				party_join=party_join,
				is_opening_condition=is_opening_condition,
				filter_conditions=filter_conditions
			), self.filters, as_dict=1)

			for d in additional_customer_info:
				self.additional_customer_info[d.customer] = d

	def get_itemised_taxes(self):
		if self.entries:
			self.itemised_tax, self.tax_columns = get_tax_accounts(self.entries, [], self.company_currency, self.filters.doctype,
				"Sales Taxes and Charges" if self.filters.party_type == "Customer" else "Purchase Taxes and Charges")
			self.tax_amount_fields = ["tax_" + scrub(tax) for tax in self.tax_columns]
			self.tax_rate_fields = ["tax_" + scrub(tax) + "_rate" for tax in self.tax_columns]
		else:
			self.itemised_tax, self.tax_columns = {}, []
			self.tax_amount_fields, self.tax_rate_fields = [], []

	def prepare_data(self):
		for d in self.entries:
			# Set UOM based on qty field
			if self.filters.qty_field == "Transaction Qty":
				d.uom = d.uom
			elif self.filters.qty_field == "Contents Qty":
				d.uom = d.alt_uom or d.stock_uom
			else:
				d.uom = d.stock_uom

			# Add additional fields
			d.update({
				"doc_type": "Item",
				"reference": d.item_code,
				"voucher_no": d.parent,
				"group_doctype": "Item Group",
				"group": d.item_group,
				"brand": d.brand,
				"cost_center": d.parent_cost_center or d.item_cost_center,
				"project": d.item_project or d.parent_project,
				scrub(self.filters.party_type) + "_name": d.party_name,
				"party_name": d.party_name,
				"disable_item_formatter": cint(self.show_item_name),
				"disable_party_name_formatter": cint(self.show_party_name),
				"applies_to_variant_of": d.applies_to_variant_of or d.applies_to_item,
			})

			if "Group by Item" in [self.filters.group_by_1, self.filters.group_by_2, self.filters.group_by_3]:
				d['doc_type'] = self.filters.doctype
				d['reference'] = d.get("voucher_no")

			# Add tax fields
			for f, tax in zip(self.tax_amount_fields, self.tax_columns):
				tax_amount = self.itemised_tax.get(d.name, {}).get(tax, {}).get("tax_amount", 0.0)
				d[f] = flt(tax_amount)
			for f, tax in zip(self.tax_rate_fields, self.tax_columns):
				tax_rate = self.itemised_tax.get(d.name, {}).get(tax, {}).get("tax_rate", 0.0)
				d[f] = flt(tax_rate)

			self.postprocess_row(d)
			self.apply_sales_person_contribution(d)

	def get_grouped_data(self):
		data = self.entries

		self.group_by = [None]
		for i in range(3):
			group_label = self.filters.get("group_by_" + str(i + 1), "").replace("Group by ", "")

			if not group_label or group_label == "Ungrouped":
				continue
			if group_label in ['Customer', 'Supplier']:
				group_field = "party"
			elif group_label == "Transaction":
				group_field = "voucher_no"
			elif group_label == "Item":
				group_field = "item_code"
			elif group_label in ["Customer Group", "Supplier Group"]:
				group_field = "party_group"
			else:
				group_field = scrub(group_label)

			self.group_by.append(group_field)

		# Group same items
		if cint(self.filters.get("group_same_items")) and not self.filters.totals_only:
			data = group_report_data(data, ("item_code", "item_name", "uom", "voucher_no"), calculate_totals=self.calculate_group_totals,
				totals_only=True)

		if len(self.group_by) <= 1:
			return data

		return group_report_data(data, self.group_by, calculate_totals=self.calculate_group_totals,
			totals_only=self.filters.totals_only)

	def calculate_group_totals(self, data, group_field, group_value, grouped_by):
		total_fields = ['qty'] + self.amount_fields + self.tax_amount_fields
		if self.filters.sales_person:
			total_fields.append('actual_net_amount')

		averageif_fields = self.tax_rate_fields

		totals = {
			"disable_item_formatter": cint(self.show_item_name),
			"disable_party_name_formatter": cint(self.show_party_name)
		}

		# Copy grouped by into total row
		for f, g in iteritems(grouped_by):
			totals[f] = g

		# Set zeros
		for f in total_fields + averageif_fields + [f + "_count" for f in averageif_fields]:
			totals[f] = 0

		# Add totals
		for d in data:
			for f in total_fields:
				totals[f] += flt(d[f])

			for f in averageif_fields:
				if flt(d[f]):
					totals[f] += flt(d[f])
					totals[f + "_count"] += 1

		# Set group values
		if data:
			if group_field == ("item_code", "item_name", "uom", "voucher_no"):
				for f, v in iteritems(data[0]):
					if f not in totals:
						totals[f] = v

			if 'voucher_no' in grouped_by:
				fields_to_copy = ['date', 'sales_person', 'territory', 'party', 'party_name', 'bill_no', 'bill_date']
				for f in fields_to_copy:
					if f in data[0]:
						totals[f] = data[0][f]
				totals['date'] = data[0].get('date')
				totals['stin'] = data[0].get('stin')

				projects = set([d.get('project') for d in data if d.get('project')])
				totals['project'] = ", ".join(projects)

			if 'item_code' in grouped_by:
				totals['item_name'] = data[0].get('item_name')
				totals['group_doctype'] = "Item Group"
				totals['group'] = data[0].get('item_group')
				totals['brand'] = data[0].get('brand')

			if group_field in ('applies_to_item', 'applies_to_variant_of'):
				totals['item_name'] = frappe.db.get_value("Item", group_value, 'item_name', cache=1) if group_value else None
				totals['group_doctype'] = "Item Group"
				totals['group'] = frappe.db.get_value("Item", group_value, 'item_group', cache=1) if group_value else None
				totals['brand'] = frappe.db.get_value("Item", group_value, 'brand', cache=1) if group_value else None

			if group_field == 'party':
				totals['group_doctype'] = data[0].get("party_group_dt")
				totals['group'] = data[0].get("party_group")
				totals['party_name'] = data[0].get("party_name")
				totals['party_type'] = self.filters.party_type

				if self.filters.party_type == "Customer":
					details = self.additional_customer_info.get(group_value, frappe._dict())
					totals.update({
						"sales_person": grouped_by.get("sales_person") or details.sales_person,
						"territory": grouped_by.get("territory") or details.territory,
						"allocated_percentage": details.allocated_percentage
					})

		# Set reference field
		group_reference_doctypes = {
			"party": self.filters.party_type,
			"voucher_no": self.filters.doctype,
			"item_code": "Item",
			"applies_to_item": "Item",
			"applies_to_variant_of": "Item",
		}

		if group_field == ("item_code", "item_nane", "uom", "voucher_no") and data:
			totals['doc_type'] = data[0].get('doc_type')
			totals['reference'] = data[0].get('reference')
		else:
			reference_field = group_field[0] if isinstance(group_field, (list, tuple)) else group_field
			reference_dt = group_reference_doctypes.get(reference_field, unscrub(cstr(reference_field)))
			totals['doc_type'] = reference_dt
			totals['reference'] = grouped_by.get(reference_field) if group_field else "'Total'"

			if not group_field and self.group_by == [None]:
				totals['voucher_no'] = "'Total'"

		# Calculate sales person contribution percentage
		if totals.get('actual_net_amount'):
			totals['allocated_percentage'] = totals['base_net_amount'] / totals['actual_net_amount'] * 100

		self.postprocess_row(totals)
		return totals

	def postprocess_row(self, row):
		# Calculate rate
		if flt(row['qty']):
			for d in self.rate_fields:
				divisor_field = 'qty'
				multiplier = 1

				if len(d) == 2:
					target, source = d
				elif len(d) == 3:
					target, source, divisor_field = d
				else:
					target, source, divisor_field, multiplier = d

				if flt(row[divisor_field]):
					row[target] = flt(row[source]) / flt(row[divisor_field]) * flt(multiplier)
				else:
					row[target] = 0

		# Calculate total taxes and grand total
		row["total_tax_amount"] = 0.0
		for f in self.tax_amount_fields:
			row["total_tax_amount"] += row[f]

		row["grand_total"] = row["base_net_amount"] + row["total_tax_amount"]

		# Calculate tax rates by averaging
		for f in self.tax_rate_fields:
			row[f] = row.get(f, 0.0)
			if flt(row.get(f + "_count")):
				row[f] /= flt(row.get(f + "_count"))

			if f + "_count" in row:
				del row[f + "_count"]

	def apply_sales_person_contribution(self, row):
		if self.filters.sales_person:
			row['actual_net_amount'] = row["base_net_amount"]

			fields = ['qty', 'total_tax_amount', 'grand_total'] + self.amount_fields + self.tax_amount_fields
			for f in fields:
				row[f] *= row.allocated_percentage / 100

	def get_qty_fieldname(self):
		filter_to_field = {
			"Stock Qty": "stock_qty",
			"Contents Qty": "alt_uom_qty",
			"Transaction Qty": "qty"
		}
		return filter_to_field.get(self.filters.qty_field) or "stock_qty"

	def get_conditions(self):
		conditions = []

		if self.filters.get("company"):
			conditions.append("s.company = %(company)s")

		if self.filters.get("customer"):
			conditions.append("s.customer = %(customer)s")

		if self.filters.get("customer_group"):
			lft, rgt = frappe.db.get_value("Customer Group", self.filters.customer_group, ["lft", "rgt"])
			conditions.append("""cus.customer_group in (select name from `tabCustomer Group`
				where lft >= {0} and rgt <= {1})""".format(lft, rgt))

		if self.filters.get("supplier"):
			conditions.append("s.supplier = %(supplier)s")

		if self.filters.get("supplier_group"):
			lft, rgt = frappe.db.get_value("Supplier Group", self.filters.supplier_group, ["lft", "rgt"])
			conditions.append("""sup.supplier_group in (select name from `tabSupplier Group`
				where lft >= {0} and rgt <= {1})""".format(lft, rgt))

		if self.filters.get("item_code"):
			is_template = frappe.db.get_value("Item", self.filters.get('item_code'), 'has_variants')
			if is_template:
				conditions.append("im.variant_of = %(item_code)s")
			else:
				conditions.append("im.name = %(item_code)s")

		if self.filters.get("applies_to_item"):
			is_template = frappe.db.get_value("Item", self.filters.get('applies_to_item'), 'has_variants')
			if is_template:
				self.filters.applies_to_items = [self.filters.applies_to_item]
				self.filters.applies_to_items += [d.name for d in frappe.get_all("Item", {'variant_of': self.filters.applies_to_item})]
				conditions.append("s.applies_to_item in %(applies_to_items)s")
			else:
				conditions.append("s.applies_to_item = %(applies_to_item)s")

		if self.filters.get("item_group"):
			lft, rgt = frappe.db.get_value("Item Group", self.filters.item_group, ["lft", "rgt"])
			conditions.append("""im.item_group in (select name from `tabItem Group`
				where lft >= {0} and rgt <= {1})""".format(lft, rgt))

		if self.filters.get("brand"):
			conditions.append("im.brand = %(brand)s")

		if self.filters.get("item_source"):
			conditions.append("im.item_source = %(item_source)s")

		if self.filters.get("territory"):
			lft, rgt = frappe.db.get_value("Territory", self.filters.territory, ["lft", "rgt"])
			conditions.append("""s.territory in (select name from `tabTerritory`
				where lft >= {0} and rgt <= {1})""".format(lft, rgt))

		if self.filters.get("sales_person"):
			lft, rgt = frappe.db.get_value("Sales Person", self.filters.sales_person, ["lft", "rgt"])
			conditions.append("""sp.sales_person in (select name from `tabSales Person`
				where lft >= {0} and rgt <= {1})""".format(lft, rgt))

		if self.filters.get("order_type"):
			conditions.append("s.order_type = %(order_type)s")

		if self.filters.get("transaction_type"):
			conditions.append("s.transaction_type = %(transaction_type)s")

		if self.filters.get("cost_center"):
			self.filters.cost_center = get_cost_centers_with_children(self.filters.get("cost_center"))

			if frappe.get_meta(self.filters.doctype + " Item").has_field("cost_center") and frappe.get_meta(self.filters.doctype).has_field("cost_center"):
				conditions.append("IF(s.cost_center IS NULL or s.cost_center = '', i.cost_center, s.cost_center) in %(cost_center)s")
			elif frappe.get_meta(self.filters.doctype + " Item").has_field("cost_center"):
				conditions.append("i.cost_center in %(cost_center)s")
			elif frappe.get_meta(self.filters.doctype).has_field("cost_center"):
				conditions.append("s.cost_center in %(cost_center)s")

		if self.filters.get("project"):
			if isinstance(self.filters.project, string_types):
				self.filters.project = cstr(self.filters.get("project")).strip()
				self.filters.project = [d.strip() for d in self.filters.project.split(',') if d]

			if frappe.get_meta(self.filters.doctype + " Item").has_field("project") and frappe.get_meta(self.filters.doctype).has_field("project"):
				conditions.append("IF(i.project IS NULL or i.project = '', s.project, i.project) in %(project)s")
			elif frappe.get_meta(self.filters.doctype + " Item").has_field("project"):
				conditions.append("i.project in %(project)s")
			elif frappe.get_meta(self.filters.doctype).has_field("project"):
				conditions.append("s.project in %(project)s")

		if self.filters.get("warehouse"):
			lft, rgt = frappe.db.get_value("Warehouse", self.filters.warehouse, ["lft", "rgt"])
			conditions.append("""i.warehouse in (select name from `tabWarehouse`
				where lft >= {0} and rgt <= {1})""".format(lft, rgt))

		return "and {}".format(" and ".join(conditions)) if conditions else ""

	def get_columns(self):
		party_field = {
			"label": _(self.filters.party_type),
			"fieldtype": "Link",
			"fieldname": "party",
			"options": self.filters.party_type,
			"width": 80 if self.show_party_name else 150
		}
		party_name_field = {
			"label": _(self.filters.party_type) + " Name",
			"fieldtype": "Data",
			"fieldname": "party_name",
			"width": 150
		}

		bill_no_field = {
			"label": "Bill No",
			"fieldtype": "Data",
			"fieldname": "bill_no",
			"width": 80
		}

		bill_date_field = {
			"label": "Bill Date",
			"fieldtype": "Date",
			"fieldname": "bill_date",
			"width": 80
		}

		if len(self.group_by) > 1:
			columns = [
				{
					"label": _("Reference"),
					"fieldtype": "Dynamic Link",
					"fieldname": "reference",
					"options": "doc_type",
					"width": 250
				},
				{
					"label": _("Type"),
					"fieldtype": "Data",
					"fieldname": "doc_type",
					"width": 90
				},
				{
					"label": _("Item Name"),
					"fieldtype": "Data",
					"fieldname": "item_name",
					"width": 150
				},
			]

			if frappe.get_meta(self.filters.doctype).has_field('bill_no'):
				columns += [bill_no_field]

			if frappe.get_meta(self.filters.doctype).has_field('bill_date'):
				columns += [bill_date_field]

			group_list = [self.filters.group_by_1, self.filters.group_by_2, self.filters.group_by_3]
			if "Group by Transaction" not in group_list:
				columns.append({
					"label": _(self.filters.doctype),
					"fieldtype": "Link",
					"fieldname": "voucher_no",
					"options": self.filters.doctype,
					"width": 140
				})

			columns.append(party_field)
			if self.show_party_name:
				columns.append(party_name_field)

			columns += [
				{
					"label": _("Date"),
					"fieldtype": "Date",
					"fieldname": "date",
					"width": 80
				},
			]
		else:
			columns = [
				{
					"label": _("Date"),
					"fieldtype": "Date",
					"fieldname": "date",
					"width": 80
				},
				{
					"label": _(self.filters.doctype),
					"fieldtype": "Link",
					"fieldname": "voucher_no",
					"options": self.filters.doctype,
					"width": 140
				},
			]

			if frappe.get_meta(self.filters.doctype).has_field('bill_no'):
				columns += [bill_no_field]

			if frappe.get_meta(self.filters.doctype).has_field('bill_date'):
				columns += [bill_date_field]

			if self.filters.doctype == "Sales Invoice":
				columns.append({
					"label": _("Inv #"),
					"fieldtype": "Int",
					"fieldname": "stin",
					"width": 60
				})

			columns.append(party_field)
			if self.show_party_name:
				columns.append(party_name_field)

			columns += [
				{
					"label": _("Item Code"),
					"fieldtype": "Link",
					"fieldname": "item_code",
					"options": "Item",
					"width": 100 if self.show_item_name else 150
				},
				{
					"label": _("Item Name"),
					"fieldtype": "Data",
					"fieldname": "item_name",
					"width": 150
				},
			]

		if self.filters.sales_person:
			columns.append({
				"label": _("% Contribution"),
				"fieldtype": "Percent",
				"fieldname": "allocated_percentage",
				"width": 60
			})
		columns += [
			{
				"label": _("UOM"),
				"fieldtype": "Link",
				"options": "UOM",
				"fieldname": "uom",
				"width": 50
			},
			{
				"label": _("Qty"),
				"fieldtype": "Float",
				"fieldname": "qty",
				"width": 80
			},
		]

		value_columns = [
			{
				"label": _("Rate Before Discount"),
				"fieldtype": "Currency",
				"fieldname": "base_rate_before_discount",
				"options": "Company:company:default_currency",
				"width": 120
			},
			{
				"label": _("Amount Before Discount"),
				"fieldtype": "Currency",
				"fieldname": "base_amount_before_discount",
				"options": "Company:company:default_currency",
				"width": 120
			},
			{
				"label": _("Total Discount"),
				"fieldtype": "Currency",
				"fieldname": "base_total_discount",
				"options": "Company:company:default_currency",
				"width": 120
			},
			{
				"label": _("Discount Rate"),
				"fieldtype": "Percent",
				"fieldname": "base_discount_rate",
				"options": "Company:company:default_currency",
				"width": 60
			},
			{
				"label": _("Rate"),
				"fieldtype": "Currency",
				"fieldname": "base_rate",
				"options": "Company:company:default_currency",
				"width": 120
			},
			{
				"label": _("Amount"),
				"fieldtype": "Currency",
				"fieldname": "base_amount",
				"options": "Company:company:default_currency",
				"width": 120
			},
			{
				"label": _("Rate Before Discount (Tax Exclusive)"),
				"fieldtype": "Currency",
				"fieldname": "base_tax_exclusiverate_before_discount",
				"options": "Company:company:default_currency",
				"width": 120
			},
			{
				"label": _("Amount Before Discount (Tax Exclusive)"),
				"fieldtype": "Currency",
				"fieldname": "base_tax_exclusive_amount_before_discount",
				"options": "Company:company:default_currency",
				"width": 120
			},
			{
				"label": _("Total Discount (Tax Exclusive)"),
				"fieldtype": "Currency",
				"fieldname": "base_tax_exclusive_total_discount",
				"options": "Company:company:default_currency",
				"width": 120
			},
			{
				"label": _("Discount Rate"),
				"fieldtype": "Percent",
				"fieldname": "base_tax_exclusive_discount_rate",
				"options": "Company:company:default_currency",
				"width": 60
			},
			{
				"label": _("Rate (Tax Exclusive)"),
				"fieldtype": "Currency",
				"fieldname": "base_tax_exclusive_rate",
				"options": "Company:company:default_currency",
				"width": 120
			},
			{
				"label": _("Amount (Tax Exclusive)"),
				"fieldtype": "Currency",
				"fieldname": "base_tax_exclusive_amount",
				"options": "Company:company:default_currency",
				"width": 120
			},
			{
				"label": _("Net Rate"),
				"fieldtype": "Currency",
				"fieldname": "base_net_rate",
				"options": "Company:company:default_currency",
				"width": 120
			},
			{
				"label": _("Net Amount"),
				"fieldtype": "Currency",
				"fieldname": "base_net_amount",
				"options": "Company:company:default_currency",
				"width": 120
			},
		]

		filtered_fields = self.amount_fields + [d[0] for d in self.rate_fields]
		for c in value_columns:
			if c['fieldname'] in filtered_fields:
				columns.append(c)

		columns += [
			{
				"label": _("Taxes and Charges"),
				"fieldtype": "Currency",
				"fieldname": "total_tax_amount",
				"options": "Company:company:default_currency",
				"width": 120
			},
			{
				"label": _("Grand Total"),
				"fieldtype": "Currency",
				"fieldname": "grand_total",
				"options": "Company:company:default_currency",
				"width": 120
			},
		]

		if self.filters.include_taxes:
			for tax_description in self.tax_columns:
				amount_field = "tax_" + scrub(tax_description)
				rate_field = amount_field + "_rate"
				columns += [
					{
						"label": _(tax_description) + " (%)",
						"fieldtype": "Percent",
						"fieldname": rate_field,
						"width": 60
					},
					{
						"label": _(tax_description),
						"fieldtype": "Currency",
						"fieldname": amount_field,
						"options": "Company:company:default_currency",
						"width": 120
					},
				]

		if self.filters.party_type == "Customer":
			columns += [
				{
					"label": _("Sales Person"),
					"fieldtype": "Data",
					"fieldname": "sales_person",
					"width": 150
				},
				{
					"label": _("Territory"),
					"fieldtype": "Link",
					"fieldname": "territory",
					"options": "Territory",
					"width": 100
				},
			]

		if frappe.get_meta(self.filters.doctype + " Item").has_field("cost_center"):
			columns.append({
				"label": _("Cost Center"),
				"fieldtype": "Link",
				"fieldname": "cost_center",
				"options": "Cost Center",
				"width": 100
			})

		columns += [
			{
				"label": _("Project"),
				"fieldtype": "Link",
				"fieldname": "project",
				"options": "Project",
				"width": 100
			},
			{
				"label": _("Group"),
				"fieldtype": "Dynamic Link",
				"fieldname": "group",
				"options": "group_doctype",
				"width": 100
			},
			{
				"label": _("Brand"),
				"fieldtype": "Link",
				"fieldname": "brand",
				"options": "Brand",
				"width": 100
			},
		]

		if not self.show_item_name:
			columns = [c for c in columns if c.get('fieldname') != 'item_name']

		return columns

def execute(filters=None):
	return SalesPurchaseDetailsReport(filters).run("Customer")
