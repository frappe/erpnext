# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe, erpnext
from frappe.utils import cint, cstr, flt
from frappe import _
from erpnext.setup.utils import get_exchange_rate
from frappe.website.website_generator import WebsiteGenerator
from erpnext.stock.get_item_details import get_conversion_factor

import functools

from six import string_types

from operator import itemgetter

form_grid_templates = {
	"items": "templates/form_grid/item_grid.html"
}

class BOM(WebsiteGenerator):
	website = frappe._dict(
		# page_title_field = "item_name",
		condition_field = "show_in_website",
		template = "templates/generators/bom.html"
	)

	def autoname(self):
		names = frappe.db.sql_list("""select name from `tabBOM` where item=%s""", self.item)

		if names:
			# name can be BOM/ITEM/001, BOM/ITEM/001-1, BOM-ITEM-001, BOM-ITEM-001-1

			# split by item
			names = [name.split(self.item)[-1][1:] for name in names]

			# split by (-) if cancelled
			names = [cint(name.split('-')[-1]) for name in names]

			idx = max(names) + 1
		else:
			idx = 1

		self.name = 'BOM-' + self.item + ('-%.3i' % idx)

	def validate(self):
		self.route = frappe.scrub(self.name).replace('_', '-')
		self.clear_operations()
		self.validate_main_item()
		self.validate_currency()
		self.set_conversion_rate()
		self.validate_uom_is_interger()
		self.set_bom_material_details()
		self.validate_materials()
		self.validate_operations()
		self.calculate_cost()

	def get_context(self, context):
		context.parents = [{'name': 'boms', 'title': _('All BOMs') }]

	def on_update(self):
		self.check_recursion()
		self.update_stock_qty()
		self.update_exploded_items()

	def on_submit(self):
		self.manage_default_bom()

	def on_cancel(self):
		frappe.db.set(self, "is_active", 0)
		frappe.db.set(self, "is_default", 0)

		# check if used in any other bom
		self.validate_bom_links()
		self.manage_default_bom()

	def on_update_after_submit(self):
		self.validate_bom_links()
		self.manage_default_bom()

	def get_item_det(self, item_code):
		item = frappe.db.sql("""select name, item_name, docstatus, description, image,
			is_sub_contracted_item, stock_uom, default_bom, last_purchase_rate, allow_transfer_for_manufacture
			from `tabItem` where name=%s""", item_code, as_dict = 1)

		if not item:
			frappe.throw(_("Item: {0} does not exist in the system").format(item_code))

		return item

	def get_routing(self):
		if self.routing:
			for d in frappe.get_all("BOM Operation", fields = ["*"],
				filters = {'parenttype': 'Routing', 'parent': self.routing}):
				child = self.append('operations', d)
				child.hour_rate = flt(d.hour_rate / self.conversion_rate, 2)

	def validate_rm_item(self, item):
		if (item[0]['name'] in [it.item_code for it in self.items]) and item[0]['name'] == self.item:
			frappe.throw(_("BOM #{0}: Raw material cannot be same as main Item").format(self.name))

	def set_bom_material_details(self):
		for item in self.get("items"):
			self.validate_bom_currecny(item)

			ret = self.get_bom_material_detail({
				"item_code": item.item_code,
				"item_name": item.item_name,
				"bom_no": item.bom_no,
				"stock_qty": item.stock_qty,
				"allow_transfer_for_manufacture": item.allow_transfer_for_manufacture
			})
			for r in ret:
				if not item.get(r):
					item.set(r, ret[r])

	def get_bom_material_detail(self, args=None):
		""" Get raw material details like uom, desc and rate"""
		if not args:
			args = frappe.form_dict.get('args')

		if isinstance(args, string_types):
			import json
			args = json.loads(args)

		item = self.get_item_det(args['item_code'])
		self.validate_rm_item(item)

		args['bom_no'] = args['bom_no'] or item and cstr(item[0]['default_bom']) or ''
		args['transfer_for_manufacture'] = (cstr(args.get('allow_transfer_for_manufacture', '')) or
			item and item[0].allow_transfer_for_manufacture or 0)
		args.update(item[0])

		rate = self.get_rm_rate(args)
		ret_item = {
			 'item_name'	: item and args['item_name'] or '',
			 'description'  : item and args['description'] or '',
			 'image'		: item and args['image'] or '',
			 'stock_uom'	: item and args['stock_uom'] or '',
			 'uom'			: item and args['stock_uom'] or '',
 			 'conversion_factor': 1,
			 'bom_no'		: args['bom_no'],
			 'rate'			: rate / self.conversion_rate if self.conversion_rate else rate,
			 'qty'			: args.get("qty") or args.get("stock_qty") or 1,
			 'stock_qty'	: args.get("qty") or args.get("stock_qty") or 1,
			 'base_rate'	: rate,
			 'allow_transfer_for_manufacture': cint(args['transfer_for_manufacture']) or 0
		}

		return ret_item

	def validate_bom_currecny(self, item):
		if item.get('bom_no') and frappe.db.get_value('BOM', item.get('bom_no'), 'currency') != self.currency:
			frappe.throw(_("Row {0}: Currency of the BOM #{1} should be equal to the selected currency {2}")
				.format(item.idx, item.bom_no, self.currency))

	def get_rm_rate(self, arg):
		"""	Get raw material rate as per selected method, if bom exists takes bom cost """
		rate = 0

		if arg.get('scrap_items'):
			rate = self.get_valuation_rate(arg)
		elif arg:
			if arg.get('bom_no') and self.set_rate_of_sub_assembly_item_based_on_bom:
				rate = self.get_bom_unitcost(arg['bom_no'])
			else:
				if self.rm_cost_as_per == 'Valuation Rate':
					rate = self.get_valuation_rate(arg)
				elif self.rm_cost_as_per == 'Last Purchase Rate':
					rate = arg.get('last_purchase_rate') \
						or frappe.db.get_value("Item", arg['item_code'], "last_purchase_rate")
				elif self.rm_cost_as_per == "Price List":
					if not self.buying_price_list:
						frappe.throw(_("Please select Price List"))
					rate = frappe.db.get_value("Item Price", {"price_list": self.buying_price_list,
						"item_code": arg["item_code"]}, "price_list_rate") or 0.0

					price_list_currency = frappe.db.get_value("Price List",
						self.buying_price_list, "currency")
					if price_list_currency != self.company_currency():
						rate = flt(rate * self.conversion_rate)

				if not rate:
					frappe.msgprint(_("{0} not found for Item {1}")
						.format(self.rm_cost_as_per, arg["item_code"]), alert=True)

		return flt(rate)

	def update_cost(self, update_parent=True, from_child_bom=False):
		if self.docstatus == 2:
			return

		existing_bom_cost = self.total_cost

		for d in self.get("items"):
			rate = self.get_rm_rate({"item_code": d.item_code, "bom_no": d.bom_no})
			if rate:
				d.rate = rate * flt(d.conversion_factor) / flt(self.conversion_rate)

		if self.docstatus == 1:
			self.flags.ignore_validate_update_after_submit = True
			self.calculate_cost()
		self.save()
		self.update_exploded_items()

		# update parent BOMs
		if self.total_cost != existing_bom_cost and update_parent:
			parent_boms = frappe.db.sql_list("""select distinct parent from `tabBOM Item`
				where bom_no = %s and docstatus=1 and parenttype='BOM'""", self.name)

			for bom in parent_boms:
				frappe.get_doc("BOM", bom).update_cost(from_child_bom=True)

		if not from_child_bom:
			frappe.msgprint(_("Cost Updated"))

	def update_parent_cost(self):
		if self.total_cost:
			cost = self.total_cost / self.quantity

			frappe.db.sql("""update `tabBOM Item` set rate=%s, amount=stock_qty*%s
				where bom_no = %s and docstatus < 2 and parenttype='BOM'""",
				(cost, cost, self.name))

	def get_bom_unitcost(self, bom_no):
		bom = frappe.db.sql("""select name, base_total_cost/quantity as unit_cost from `tabBOM`
			where is_active = 1 and name = %s""", bom_no, as_dict=1)
		return bom and bom[0]['unit_cost'] or 0

	def get_valuation_rate(self, args):
		""" Get weighted average of valuation rate from all warehouses """

		total_qty, total_value, valuation_rate = 0.0, 0.0, 0.0
		for d in frappe.db.sql("""select actual_qty, stock_value from `tabBin`
			where item_code=%s""", args['item_code'], as_dict=1):
				total_qty += flt(d.actual_qty)
				total_value += flt(d.stock_value)

		if total_qty:
			valuation_rate =  total_value / total_qty

		if valuation_rate <= 0:
			last_valuation_rate = frappe.db.sql("""select valuation_rate
				from `tabStock Ledger Entry`
				where item_code = %s and valuation_rate > 0
				order by posting_date desc, posting_time desc, name desc limit 1""", args['item_code'])

			valuation_rate = flt(last_valuation_rate[0][0]) if last_valuation_rate else 0

		if not valuation_rate:
			valuation_rate = frappe.db.get_value("Item", args['item_code'], "valuation_rate")

		return valuation_rate

	def manage_default_bom(self):
		""" Uncheck others if current one is selected as default,
			update default bom in item master
		"""
		if self.is_default and self.is_active:
			from frappe.model.utils import set_default
			set_default(self, "item")
			item = frappe.get_doc("Item", self.item)
			if item.default_bom != self.name:
				frappe.db.set_value('Item', self.item, 'default_bom', self.name)
		else:
			frappe.db.set(self, "is_default", 0)
			item = frappe.get_doc("Item", self.item)
			if item.default_bom == self.name:
				frappe.db.set_value('Item', self.item, 'default_bom', None)

	def clear_operations(self):
		if not self.with_operations:
			self.set('operations', [])

	def validate_main_item(self):
		""" Validate main FG item"""
		item = self.get_item_det(self.item)
		if not item:
			frappe.throw(_("Item {0} does not exist in the system or has expired").format(self.item))
		else:
			ret = frappe.db.get_value("Item", self.item, ["description", "stock_uom", "item_name"])
			self.description = ret[0]
			self.uom = ret[1]
			self.item_name= ret[2]

		if not self.quantity:
			frappe.throw(_("Quantity should be greater than 0"))

	def validate_currency(self):
		if self.rm_cost_as_per == 'Price List':
			price_list_currency = frappe.db.get_value('Price List', self.buying_price_list, 'currency')
			if price_list_currency not in (self.currency, self.company_currency()):
				frappe.throw(_("Currency of the price list {0} must be {1} or {2}")
					.format(self.buying_price_list, self.currency, self.company_currency()))

	def update_stock_qty(self):
		for m in self.get('items'):
			if not m.conversion_factor:
				m.conversion_factor = flt(get_conversion_factor(m.item_code, m.uom)['conversion_factor'])
			if m.uom and m.qty:
				m.stock_qty = flt(m.conversion_factor)*flt(m.qty)
			if not m.uom and m.stock_uom:
				m.uom = m.stock_uom
				m.qty = m.stock_qty

			m.db_update()

	def validate_uom_is_interger(self):
		from erpnext.utilities.transaction_base import validate_uom_is_integer
		validate_uom_is_integer(self, "uom", "qty", "BOM Item")
		validate_uom_is_integer(self, "stock_uom", "stock_qty", "BOM Item")

	def set_conversion_rate(self):
		if self.currency == self.company_currency():
			self.conversion_rate = 1
		elif self.conversion_rate == 1 or flt(self.conversion_rate) <= 0:
			self.conversion_rate = get_exchange_rate(self.currency, self.company_currency(), args="for_buying")

	def validate_materials(self):
		""" Validate raw material entries """

		def get_duplicates(lst):
			seen = set()
			seen_add = seen.add
			for item in lst:
				if item.item_code in seen or seen_add(item.item_code):
					yield item

		if not self.get('items'):
			frappe.throw(_("Raw Materials cannot be blank."))
		check_list = []
		for m in self.get('items'):
			if m.bom_no:
				validate_bom_no(m.item_code, m.bom_no)
			if flt(m.qty) <= 0:
				frappe.throw(_("Quantity required for Item {0} in row {1}").format(m.item_code, m.idx))
			check_list.append(m)

		if not self.allow_same_item_multiple_times:
			duplicate_items = list(get_duplicates(check_list))
			if duplicate_items:
				li = []
				for i in duplicate_items:
					li.append("{0} on row {1}".format(i.item_code, i.idx))
				duplicate_list = '<br>' + '<br>'.join(li)

				frappe.throw(_("Same item has been entered multiple times. {0}").format(duplicate_list))

	def check_recursion(self):
		""" Check whether recursion occurs in any bom"""
		bom_list = self.traverse_tree()
		bom_nos = frappe.get_all('BOM Item', fields=["bom_no"],
			filters={'parent': ('in', bom_list), 'parenttype': 'BOM'})

		raise_exception = False
		if bom_nos and self.name in [d.bom_no for d in bom_nos]:
			raise_exception = True

		if not raise_exception:
			bom_nos = frappe.get_all('BOM Item', fields=["parent"],
				filters={'bom_no': self.name, 'parenttype': 'BOM'})

			if self.name in [d.parent for d in bom_nos]:
				raise_exception = True

		if raise_exception:
			frappe.throw(_("BOM recursion: {0} cannot be parent or child of {2}").format(self.name, self.name))

	def update_cost_and_exploded_items(self, bom_list=[]):
		bom_list = self.traverse_tree(bom_list)
		for bom in bom_list:
			bom_obj = frappe.get_doc("BOM", bom)
			bom_obj.check_recursion()
			bom_obj.update_exploded_items()

		return bom_list

	def traverse_tree(self, bom_list=None):
		def _get_children(bom_no):
			return [cstr(d[0]) for d in frappe.db.sql("""select bom_no from `tabBOM Item`
				where parent = %s and ifnull(bom_no, '') != '' and parenttype='BOM'""", bom_no)]

		count = 0
		if not bom_list:
			bom_list = []

		if self.name not in bom_list:
			bom_list.append(self.name)

		while(count < len(bom_list)):
			for child_bom in _get_children(bom_list[count]):
				if child_bom not in bom_list:
					bom_list.append(child_bom)
			count += 1
		bom_list.reverse()
		return bom_list

	def calculate_cost(self):
		"""Calculate bom totals"""
		self.calculate_op_cost()
		self.calculate_rm_cost()
		self.calculate_sm_cost()
		self.total_cost = self.operating_cost + self.raw_material_cost - self.scrap_material_cost
		self.base_total_cost = self.base_operating_cost + self.base_raw_material_cost - self.base_scrap_material_cost

	def calculate_op_cost(self):
		"""Update workstation rate and calculates totals"""
		self.operating_cost = 0
		self.base_operating_cost = 0
		for d in self.get('operations'):
			if d.workstation:
				if not d.hour_rate:
					hour_rate = flt(frappe.db.get_value("Workstation", d.workstation, "hour_rate"))
					d.hour_rate = hour_rate / flt(self.conversion_rate) if self.conversion_rate else hour_rate

			if d.hour_rate and d.time_in_mins:
				d.base_hour_rate = flt(d.hour_rate) * flt(self.conversion_rate)
				d.operating_cost = flt(d.hour_rate) * flt(d.time_in_mins) / 60.0
				d.base_operating_cost = flt(d.operating_cost) * flt(self.conversion_rate)

			self.operating_cost += flt(d.operating_cost)
			self.base_operating_cost += flt(d.base_operating_cost)

	def calculate_rm_cost(self):
		"""Fetch RM rate as per today's valuation rate and calculate totals"""
		total_rm_cost = 0
		base_total_rm_cost = 0

		for d in self.get('items'):
			d.base_rate = flt(d.rate) * flt(self.conversion_rate)
			d.amount = flt(d.rate, d.precision("rate")) * flt(d.qty, d.precision("qty"))
			d.base_amount = d.amount * flt(self.conversion_rate)
			d.qty_consumed_per_unit = flt(d.stock_qty, d.precision("stock_qty")) \
				/ flt(self.quantity, self.precision("quantity"))

			total_rm_cost += d.amount
			base_total_rm_cost += d.base_amount

		self.raw_material_cost = total_rm_cost
		self.base_raw_material_cost = base_total_rm_cost

	def calculate_sm_cost(self):
		"""Fetch RM rate as per today's valuation rate and calculate totals"""
		total_sm_cost = 0
		base_total_sm_cost = 0

		for d in self.get('scrap_items'):
			d.base_rate = flt(d.rate, d.precision("rate")) * flt(self.conversion_rate, self.precision("conversion_rate"))
			d.amount = flt(d.rate, d.precision("rate")) * flt(d.stock_qty, d.precision("stock_qty"))
			d.base_amount = flt(d.amount, d.precision("amount")) * flt(self.conversion_rate, self.precision("conversion_rate"))
			total_sm_cost += d.amount
			base_total_sm_cost += d.base_amount

		self.scrap_material_cost = total_sm_cost
		self.base_scrap_material_cost = base_total_sm_cost

	def update_exploded_items(self):
		""" Update Flat BOM, following will be correct data"""
		self.get_exploded_items()
		self.add_exploded_items()

	def get_exploded_items(self):
		""" Get all raw materials including items from child bom"""
		self.cur_exploded_items = {}
		for d in self.get('items'):
			if d.bom_no:
				self.get_child_exploded_items(d.bom_no, d.stock_qty)
			else:
				self.add_to_cur_exploded_items(frappe._dict({
					'item_code'		: d.item_code,
					'item_name'		: d.item_name,
					'operation'		: d.operation,
					'source_warehouse': d.source_warehouse,
					'description'	: d.description,
					'image'			: d.image,
					'stock_uom'		: d.stock_uom,
					'stock_qty'		: flt(d.stock_qty),
					'rate'			: d.base_rate,
					'allow_transfer_for_manufacture': d.allow_transfer_for_manufacture
				}))

	def company_currency(self):
		return erpnext.get_company_currency(self.company)

	def add_to_cur_exploded_items(self, args):
		if self.cur_exploded_items.get(args.item_code):
			self.cur_exploded_items[args.item_code]["stock_qty"] += args.stock_qty
		else:
			self.cur_exploded_items[args.item_code] = args

	def get_child_exploded_items(self, bom_no, stock_qty):
		""" Add all items from Flat BOM of child BOM"""
		# Did not use qty_consumed_per_unit in the query, as it leads to rounding loss
		child_fb_items = frappe.db.sql("""select bom_item.item_code, bom_item.item_name,
			bom_item.description, bom_item.source_warehouse, bom_item.operation,
			bom_item.stock_uom, bom_item.stock_qty, bom_item.rate, bom_item.allow_transfer_for_manufacture,
			bom_item.stock_qty / ifnull(bom.quantity, 1) as qty_consumed_per_unit
			from `tabBOM Explosion Item` bom_item, tabBOM bom
			where bom_item.parent = bom.name and bom.name = %s and bom.docstatus = 1""", bom_no, as_dict = 1)

		for d in child_fb_items:
			self.add_to_cur_exploded_items(frappe._dict({
				'item_code'				: d['item_code'],
				'item_name'				: d['item_name'],
				'source_warehouse'		: d['source_warehouse'],
				'operation'				: d['operation'],
				'description'			: d['description'],
				'stock_uom'				: d['stock_uom'],
				'stock_qty'				: d['qty_consumed_per_unit'] * stock_qty,
				'rate'					: flt(d['rate']),
				'allow_transfer_for_manufacture': d.get('allow_transfer_for_manufacture', 0)
			}))

	def add_exploded_items(self):
		"Add items to Flat BOM table"
		frappe.db.sql("""delete from `tabBOM Explosion Item` where parent=%s""", self.name)
		self.set('exploded_items', [])

		for d in sorted(self.cur_exploded_items, key=itemgetter(0)):
			ch = self.append('exploded_items', {})
			for i in self.cur_exploded_items[d].keys():
				ch.set(i, self.cur_exploded_items[d][i])
			ch.amount = flt(ch.stock_qty) * flt(ch.rate)
			ch.qty_consumed_per_unit = flt(ch.stock_qty) / flt(self.quantity)
			ch.docstatus = self.docstatus
			ch.db_insert()

	def validate_bom_links(self):
		if not self.is_active:
			act_pbom = frappe.db.sql("""select distinct bom_item.parent from `tabBOM Item` bom_item
				where bom_item.bom_no = %s and bom_item.docstatus = 1 and bom_item.parenttype='BOM'
				and exists (select * from `tabBOM` where name = bom_item.parent
					and docstatus = 1 and is_active = 1)""", self.name)

			if act_pbom and act_pbom[0][0]:
				frappe.throw(_("Cannot deactivate or cancel BOM as it is linked with other BOMs"))

	def validate_operations(self):
		if self.with_operations and not self.get('operations'):
			frappe.throw(_("Operations cannot be left blank"))

		if self.with_operations:
			for d in self.operations:
				if not d.description:
					d.description = frappe.db.get_value('Operation', d.operation, 'description')

def get_list_context(context):
	context.title = _("Bill of Materials")
	# context.introduction = _('Boms')

def get_bom_items_as_dict(bom, company, qty=1, fetch_exploded=1, fetch_scrap_items=0, include_non_stock_items=False):
	item_dict = {}

	# Did not use qty_consumed_per_unit in the query, as it leads to rounding loss
	query = """select
				bom_item.item_code,
				bom_item.idx,
				item.item_name,
				sum(bom_item.stock_qty/ifnull(bom.quantity, 1)) * %(qty)s as qty,
				item.description,
				item.image,
				item.stock_uom,
				item.allow_alternative_item,
				item_default.default_warehouse,
				item_default.expense_account as expense_account,
				item_default.buying_cost_center as cost_center
				{select_columns}
			from
				`tab{table}` bom_item
				JOIN `tabBOM` bom ON bom_item.parent = bom.name
				JOIN `tabItem` item ON item.name = bom_item.item_code
				LEFT JOIN `tabItem Default` item_default
					ON item_default.parent = item.name and item_default.company = %(company)s
			where
				bom_item.docstatus < 2
				and bom.name = %(bom)s
				and item.is_stock_item in (1, {is_stock_item})
				{where_conditions}
				group by item_code, stock_uom
				order by idx"""

	is_stock_item = 0 if include_non_stock_items else 1
	if cint(fetch_exploded):
		query = query.format(table="BOM Explosion Item",
			where_conditions="",
			is_stock_item=is_stock_item,
			select_columns = """, bom_item.source_warehouse, bom_item.operation, bom_item.allow_transfer_for_manufacture,
				(Select idx from `tabBOM Item` where item_code = bom_item.item_code and parent = %(parent)s ) as idx""")

		items = frappe.db.sql(query, { "parent": bom, "qty": qty, "bom": bom, "company": company }, as_dict=True)
	elif fetch_scrap_items:
		query = query.format(table="BOM Scrap Item", where_conditions="", select_columns=", bom_item.idx", is_stock_item=is_stock_item)
		items = frappe.db.sql(query, { "qty": qty, "bom": bom, "company": company }, as_dict=True)
	else:
		query = query.format(table="BOM Item", where_conditions="", is_stock_item=is_stock_item,
			select_columns = ", bom_item.source_warehouse, bom_item.idx, bom_item.operation, bom_item.allow_transfer_for_manufacture")
		items = frappe.db.sql(query, { "qty": qty, "bom": bom, "company": company }, as_dict=True)

	for item in items:
		if item.item_code in item_dict:
			item_dict[item.item_code]["qty"] += flt(item.qty)
		else:
			item_dict[item.item_code] = item

	for item, item_details in item_dict.items():
		for d in [["Account", "expense_account", "default_expense_account"],
			["Cost Center", "cost_center", "cost_center"], ["Warehouse", "default_warehouse", ""]]:
				company_in_record = frappe.db.get_value(d[0], item_details.get(d[1]), "company")
				if not item_details.get(d[1]) or (company_in_record and company != company_in_record):
					item_dict[item][d[1]] = frappe.get_cached_value('Company',  company,  d[2]) if d[2] else None

	return item_dict

@frappe.whitelist()
def get_bom_items(bom, company, qty=1, fetch_exploded=1):
	items = get_bom_items_as_dict(bom, company, qty, fetch_exploded, include_non_stock_items=True).values()
	items = list(items)
	items.sort(key = functools.cmp_to_key(lambda a, b: a.item_code > b.item_code and 1 or -1))
	return items

def validate_bom_no(item, bom_no):
	"""Validate BOM No of sub-contracted items"""
	bom = frappe.get_doc("BOM", bom_no)
	if not bom.is_active:
		frappe.throw(_("BOM {0} must be active").format(bom_no))
	if bom.docstatus != 1:
		if not getattr(frappe.flags, "in_test", False):
			frappe.throw(_("BOM {0} must be submitted").format(bom_no))
	if item:
		rm_item_exists = False
		for d in bom.items:
			if (d.item_code.lower() == item.lower()):
				rm_item_exists = True
		for d in bom.scrap_items:
			if (d.item_code.lower() == item.lower()):
				rm_item_exists = True
		if bom.item.lower() == item.lower() or \
			bom.item.lower() == cstr(frappe.db.get_value("Item", item, "variant_of")).lower():
 				rm_item_exists = True
		if not rm_item_exists:
			frappe.throw(_("BOM {0} does not belong to Item {1}").format(bom_no, item))

@frappe.whitelist()
def get_children(doctype, parent=None, is_root=False, **filters):
	if not parent or parent=="BOM":
		frappe.msgprint(_('Please select a BOM'))
		return

	if frappe.form_dict.parent:
		bom_doc = frappe.get_doc("BOM", frappe.form_dict.parent)
		frappe.has_permission("BOM", doc=bom_doc, throw=True)

		bom_items = frappe.get_all('BOM Item',
			fields=['item_code', 'bom_no as value', 'stock_qty'],
			filters=[['parent', '=', frappe.form_dict.parent]],
			order_by='idx')

		item_names = tuple(d.get('item_code') for d in bom_items)

		items = frappe.get_list('Item',
			fields=['image', 'description', 'name'],
			filters=[['name', 'in', item_names]]) # to get only required item dicts

		for bom_item in bom_items:
			# extend bom_item dict with respective item dict
			bom_item.update(
				# returns an item dict from items list which matches with item_code
				next(item for item in items if item.get('name')
					== bom_item.get('item_code'))
			)
			bom_item.expandable = 0 if bom_item.value in ('', None)  else 1

		return bom_items

def get_boms_in_bottom_up_order(bom_no=None):
	def _get_parent(bom_no):
		return frappe.db.sql_list("""select distinct parent from `tabBOM Item`
			where bom_no = %s and docstatus=1 and parenttype='BOM'""", bom_no)

	count = 0
	bom_list = []
	if bom_no:
		bom_list.append(bom_no)
	else:
		# get all leaf BOMs
		bom_list = frappe.db.sql_list("""select name from `tabBOM` bom where docstatus=1
			and not exists(select bom_no from `tabBOM Item`
				where parent=bom.name and ifnull(bom_no, '')!='')""")

	while(count < len(bom_list)):
		for child_bom in _get_parent(bom_list[count]):
			if child_bom not in bom_list:
				bom_list.append(child_bom)
		count += 1

	return bom_list

def add_additional_cost(stock_entry, work_order):
	# Add non stock items cost in the additional cost
	bom = frappe.get_doc('BOM', work_order.bom_no)
	table = 'exploded_items' if work_order.get('use_multi_level_bom') else 'items'

	items = {}
	for d in bom.get(table):
		items.setdefault(d.item_code, d.rate)

	non_stock_items = frappe.get_all('Item',
		fields="name", filters={'name': ('in', list(items.keys())), 'ifnull(is_stock_item, 0)': 0}, as_list=1)

	for name in non_stock_items:
		stock_entry.append('additional_costs', {
			'description': name[0],
			'amount': items.get(name[0])
		})
