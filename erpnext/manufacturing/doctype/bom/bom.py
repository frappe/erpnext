# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cint, cstr, flt

from frappe import _
from frappe.model.document import Document

class BOM(Document):

	def autoname(self):
		last_name = frappe.db.sql("""select max(name) from `tabBOM`
			where name like "BOM/%s/%%" """ % cstr(self.item).replace('"', '\\"'))
		if last_name:
			idx = cint(cstr(last_name[0][0]).split('/')[-1].split('-')[0]) + 1

		else:
			idx = 1
		self.name = 'BOM/' + self.item + ('/%.3i' % idx)

	def validate(self):
		self.clear_operations()
		self.validate_main_item()

		from erpnext.utilities.transaction_base import validate_uom_is_integer
		validate_uom_is_integer(self, "stock_uom", "qty")

		self.validate_operations()
		self.validate_materials()
		self.set_bom_material_details()
		self.calculate_cost()

	def on_update(self):
		self.check_recursion()
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
		item = frappe.db.sql("""select name, is_asset_item, is_purchase_item,
			docstatus, description, is_sub_contracted_item, stock_uom, default_bom,
			last_purchase_rate, is_manufactured_item
			from `tabItem` where name=%s""", item_code, as_dict = 1)

		return item

	def validate_rm_item(self, item):
		if item[0]['name'] == self.item:
			frappe.throw(_("Raw material cannot be same as main Item"))

	def set_bom_material_details(self):
		for item in self.get("bom_materials"):
			ret = self.get_bom_material_detail({"item_code": item.item_code, "bom_no": item.bom_no,
				"qty": item.qty})

			for r in ret:
				if not item.get(r):
					item.set(r, ret[r])

	def get_bom_material_detail(self, args=None):
		""" Get raw material details like uom, desc and rate"""
		if not args:
			args = frappe.form_dict.get('args')

		if isinstance(args, basestring):
			import json
			args = json.loads(args)

		item = self.get_item_det(args['item_code'])
		self.validate_rm_item(item)

		args['bom_no'] = args['bom_no'] or item and cstr(item[0]['default_bom']) or ''
		args.update(item[0])

		rate = self.get_rm_rate(args)
		ret_item = {
			 'description'  : item and args['description'] or '',
			 'stock_uom'	: item and args['stock_uom'] or '',
			 'bom_no'		: args['bom_no'],
			 'rate'			: rate
		}
		return ret_item

	def get_rm_rate(self, arg):
		"""	Get raw material rate as per selected method, if bom exists takes bom cost """
		rate = 0
		if arg['bom_no']:
			rate = self.get_bom_unitcost(arg['bom_no'])
		elif arg and (arg['is_purchase_item'] == 'Yes' or arg['is_sub_contracted_item'] == 'Yes'):
			if self.rm_cost_as_per == 'Valuation Rate':
				rate = self.get_valuation_rate(arg)
			elif self.rm_cost_as_per == 'Last Purchase Rate':
				rate = arg['last_purchase_rate']
			elif self.rm_cost_as_per == "Price List":
				if not self.buying_price_list:
					frappe.throw(_("Please select Price List"))
				rate = frappe.db.get_value("Item Price", {"price_list": self.buying_price_list,
					"item_code": arg["item_code"]}, "price_list_rate") or 0

		return rate

	def update_cost(self):
		if self.docstatus == 2:
			return

		for d in self.get("bom_materials"):
			d.rate = self.get_bom_material_detail({
				'item_code': d.item_code,
				'bom_no': d.bom_no,
				'qty': d.qty
			})["rate"]

		if self.docstatus == 1:
			self.ignore_validate_update_after_submit = True
			self.calculate_cost()
		self.save()

	def get_bom_unitcost(self, bom_no):
		bom = frappe.db.sql("""select name, total_variable_cost/quantity as unit_cost from `tabBOM`
			where is_active = 1 and name = %s""", bom_no, as_dict=1)
		return bom and bom[0]['unit_cost'] or 0

	def get_valuation_rate(self, args):
		""" Get weighted average of valuation rate from all warehouses """

		total_qty, total_value = 0.0, 0.0
		for d in frappe.db.sql("""select actual_qty, stock_value from `tabBin`
			where item_code=%s and actual_qty > 0""", args['item_code'], as_dict=1):
				total_qty += flt(d.actual_qty)
				total_value += flt(d.stock_value)

		return total_value / total_qty if total_qty else 0.0

	def manage_default_bom(self):
		""" Uncheck others if current one is selected as default,
			update default bom in item master
		"""
		if self.is_default and self.is_active:
			from frappe.model.utils import set_default
			set_default(self, "item")
			frappe.db.set_value("Item", self.item, "default_bom", self.name)

		else:
			if not self.is_active:
				frappe.db.set(self, "is_default", 0)

			frappe.db.sql("update `tabItem` set default_bom = null where name = %s and default_bom = %s",
				 (self.item, self.name))

	def clear_operations(self):
		if not self.with_operations:
			self.set('bom_operations', [])
			for d in self.get("bom_materials"):
				d.operation_no = None

	def validate_main_item(self):
		""" Validate main FG item"""
		item = self.get_item_det(self.item)
		if not item:
			frappe.throw(_("Item {0} does not exist in the system or has expired").format(self.item))
		elif item[0]['is_manufactured_item'] != 'Yes' \
				and item[0]['is_sub_contracted_item'] != 'Yes':
			frappe.throw(_("Item {0} must be manufactured or sub-contracted").format(self.item))
		else:
			ret = frappe.db.get_value("Item", self.item, ["description", "stock_uom"])
			self.description = ret[0]
			self.uom = ret[1]

	def validate_operations(self):
		""" Check duplicate operation no"""
		self.op = []
		for d in self.get('bom_operations'):
			if cstr(d.operation_no) in self.op:
				frappe.throw(_("Operation {0} is repeated in Operations Table").format(d.operation_no))
			else:
				# add operation in op list
				self.op.append(cstr(d.operation_no))

	def validate_materials(self):
		""" Validate raw material entries """
		check_list = []
		for m in self.get('bom_materials'):
			# check if operation no not in op table
			if self.with_operations and cstr(m.operation_no) not in self.op:
				frappe.throw(_("Operation {0} not present in Operations Table").format(m.operation_no))

			item = self.get_item_det(m.item_code)
			if item[0]['is_manufactured_item'] == 'Yes':
				if not m.bom_no:
					frappe.throw(_("BOM number is required for manufactured Item {0} in row {1}").format(m.item_code, m.idx))
				else:
					self.validate_bom_no(m.item_code, m.bom_no, m.idx)

			elif m.bom_no:
				frappe.throw(_("BOM number not allowed for non-manufactured Item {0} in row {1}").format(m.item_code, m.idx))

			if flt(m.qty) <= 0:
				frappe.throw(_("Quantity required for Item {0} in row {1}").format(m.item_code, m.idx))

			self.check_if_item_repeated(m.item_code, m.operation_no, check_list)

	def validate_bom_no(self, item, bom_no, idx):
		"""Validate BOM No of sub-contracted items"""
		bom = frappe.db.sql("""select name from `tabBOM` where name = %s and item = %s
			and is_active=1 and docstatus=1""",
			(bom_no, item), as_dict =1)
		if not bom:
			frappe.throw(_("BOM {0} for Item {1} in row {2} is inactive or not submitted").format(bom_no, item, idx))

	def check_if_item_repeated(self, item, op, check_list):
		if [cstr(item), cstr(op)] in check_list:
			frappe.throw(_("Item {0} has been entered multiple times against same operation").format(item))
		else:
			check_list.append([cstr(item), cstr(op)])

	def check_recursion(self):
		""" Check whether recursion occurs in any bom"""

		check_list = [['parent', 'bom_no', 'parent'], ['bom_no', 'parent', 'child']]
		for d in check_list:
			bom_list, count = [self.name], 0
			while (len(bom_list) > count ):
				boms = frappe.db.sql(" select %s from `tabBOM Item` where %s = %s " %
					(d[0], d[1], '%s'), cstr(bom_list[count]))
				count = count + 1
				for b in boms:
					if b[0] == self.name:
						frappe.throw(_("BOM recursion: {0} cannot be parent or child of {2}").format(b[0], self.name))
					if b[0]:
						bom_list.append(b[0])

	def update_cost_and_exploded_items(self, bom_list=[]):
		bom_list = self.traverse_tree(bom_list)
		for bom in bom_list:
			bom_obj = frappe.get_doc("BOM", bom)
			bom_obj.on_update()

		return bom_list

	def traverse_tree(self, bom_list=[]):
		def _get_children(bom_no):
			return [cstr(d[0]) for d in frappe.db.sql("""select bom_no from `tabBOM Item`
				where parent = %s and ifnull(bom_no, '') != ''""", bom_no)]

		count = 0
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
		self.total_variable_cost = self.raw_material_cost + self.operating_cost
		self.total_cost = self.total_variable_cost + self.total_fixed_cost

	def calculate_op_cost(self):
		"""Update workstation rate and calculates totals"""
		total_op_cost, fixed_cost = 0, 0
		for d in self.get('bom_operations'):
			if d.workstation:
				w = frappe.db.get_value("Workstation", d.workstation, ["hour_rate", "fixed_cycle_cost"])
				if not d.hour_rate:
					d.hour_rate = flt(w[0])

				fixed_cost += flt(w[1])

			if d.hour_rate and d.time_in_mins:
				d.operating_cost = flt(d.hour_rate) * flt(d.time_in_mins) / 60.0
			total_op_cost += flt(d.operating_cost)

		self.operating_cost = total_op_cost
		self.total_fixed_cost = fixed_cost

	def calculate_rm_cost(self):
		"""Fetch RM rate as per today's valuation rate and calculate totals"""
		total_rm_cost = 0
		for d in self.get('bom_materials'):
			if d.bom_no:
				d.rate = self.get_bom_unitcost(d.bom_no)
			d.amount = flt(d.rate, self.precision("rate", d)) * flt(d.qty, self.precision("qty", d))
			d.qty_consumed_per_unit = flt(d.qty, self.precision("qty", d)) / flt(self.quantity, self.precision("quantity"))
			total_rm_cost += d.amount

		self.raw_material_cost = total_rm_cost

	def update_exploded_items(self):
		""" Update Flat BOM, following will be correct data"""
		self.get_exploded_items()
		self.add_exploded_items()

	def get_exploded_items(self):
		""" Get all raw materials including items from child bom"""
		self.cur_exploded_items = {}
		for d in self.get('bom_materials'):
			if d.bom_no:
				self.get_child_exploded_items(d.bom_no, d.qty)
			else:
				self.add_to_cur_exploded_items(frappe._dict({
					'item_code'				: d.item_code,
					'description'			: d.description,
					'stock_uom'				: d.stock_uom,
					'qty'					: flt(d.qty),
					'rate'					: flt(d.rate),
				}))

	def add_to_cur_exploded_items(self, args):
		if self.cur_exploded_items.get(args.item_code):
			self.cur_exploded_items[args.item_code]["qty"] += args.qty
		else:
			self.cur_exploded_items[args.item_code] = args

	def get_child_exploded_items(self, bom_no, qty):
		""" Add all items from Flat BOM of child BOM"""
		# Did not use qty_consumed_per_unit in the query, as it leads to rounding loss
		child_fb_items = frappe.db.sql("""select bom_item.item_code, bom_item.description,
			bom_item.stock_uom, bom_item.qty, bom_item.rate,
			ifnull(bom_item.qty, 0 ) / ifnull(bom.quantity, 1) as qty_consumed_per_unit
			from `tabBOM Explosion Item` bom_item, tabBOM bom
			where bom_item.parent = bom.name and bom.name = %s and bom.docstatus = 1""", bom_no, as_dict = 1)

		for d in child_fb_items:
			self.add_to_cur_exploded_items(frappe._dict({
				'item_code'				: d['item_code'],
				'description'			: d['description'],
				'stock_uom'				: d['stock_uom'],
				'qty'					: d['qty_consumed_per_unit']*qty,
				'rate'					: flt(d['rate']),
			}))

	def add_exploded_items(self):
		"Add items to Flat BOM table"
		frappe.db.sql("""delete from `tabBOM Explosion Item` where parent=%s""", self.name)
		self.set('flat_bom_details', [])
		for d in self.cur_exploded_items:
			ch = self.append('flat_bom_details', {})
			for i in self.cur_exploded_items[d].keys():
				ch.set(i, self.cur_exploded_items[d][i])
			ch.amount = flt(ch.qty) * flt(ch.rate)
			ch.qty_consumed_per_unit = flt(ch.qty) / flt(self.quantity)
			ch.docstatus = self.docstatus
			ch.db_insert()

	def validate_bom_links(self):
		if not self.is_active:
			act_pbom = frappe.db.sql("""select distinct bom_item.parent from `tabBOM Item` bom_item
				where bom_item.bom_no = %s and bom_item.docstatus = 1
				and exists (select * from `tabBOM` where name = bom_item.parent
					and docstatus = 1 and is_active = 1)""", self.name)

			if act_pbom and act_pbom[0][0]:
				frappe.throw(_("Cannot deactive or cancle BOM as it is linked with other BOMs"))

def get_bom_items_as_dict(bom, qty=1, fetch_exploded=1):
	item_dict = {}

	# Did not use qty_consumed_per_unit in the query, as it leads to rounding loss
	query = """select
				bom_item.item_code,
				item.item_name,
				sum(ifnull(bom_item.qty, 0)/ifnull(bom.quantity, 1)) * %(qty)s as qty,
				item.description,
				item.stock_uom,
				item.default_warehouse,
				item.expense_account as expense_account,
				item.buying_cost_center as cost_center
			from
				`tab%(table)s` bom_item, `tabBOM` bom, `tabItem` item
			where
				bom_item.parent = bom.name
				and bom_item.docstatus < 2
				and bom_item.parent = "%(bom)s"
				and item.name = bom_item.item_code
				%(conditions)s
				group by item_code, stock_uom"""

	if fetch_exploded:
		items = frappe.db.sql(query % {
			"qty": qty,
			"table": "BOM Explosion Item",
			"bom": bom,
			"conditions": """and ifnull(item.is_pro_applicable, 'No') = 'No'
					and ifnull(item.is_sub_contracted_item, 'No') = 'No' """
		}, as_dict=True)
	else:
		items = frappe.db.sql(query % {
			"qty": qty,
			"table": "BOM Item",
			"bom": bom,
			"conditions": ""
		}, as_dict=True)

	# make unique
	for item in items:
		if item_dict.has_key(item.item_code):
			item_dict[item.item_code]["qty"] += flt(item.qty)
		else:
			item_dict[item.item_code] = item

	return item_dict

@frappe.whitelist()
def get_bom_items(bom, qty=1, fetch_exploded=1):
	items = get_bom_items_as_dict(bom, qty, fetch_exploded).values()
	items.sort(lambda a, b: a.item_code > b.item_code and 1 or -1)
	return items
