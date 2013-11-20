# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint, cstr, flt, now, nowdate
from webnotes.model.doc import addchild
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint, _



class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def autoname(self):
		last_name = webnotes.conn.sql("""select max(name) from `tabBOM` 
			where name like "BOM/%s/%%" """ % cstr(self.doc.item).replace('"', '\\"'))
		if last_name:
			idx = cint(cstr(last_name[0][0]).split('/')[-1].split('-')[0]) + 1
			
		else:
			idx = 1
		self.doc.name = 'BOM/' + self.doc.item + ('/%.3i' % idx)
	
	def validate(self):
		self.clear_operations()
		self.validate_main_item()

		from utilities.transaction_base import validate_uom_is_integer
		validate_uom_is_integer(self.doclist, "stock_uom", "qty")

		self.validate_operations()
		self.validate_materials()
		self.set_bom_material_details()
		self.calculate_cost()
		
	def on_update(self):
		self.check_recursion()
		self.update_exploded_items()
		self.doc.save()
	
	def on_submit(self):
		self.manage_default_bom()

	def on_cancel(self):
		webnotes.conn.set(self.doc, "is_active", 0)
		webnotes.conn.set(self.doc, "is_default", 0)

		# check if used in any other bom
		self.validate_bom_links()
		self.manage_default_bom()
				
	def on_update_after_submit(self):
		self.validate_bom_links()
		self.manage_default_bom()

	def get_item_det(self, item_code):
		item = webnotes.conn.sql("""select name, is_asset_item, is_purchase_item, 
			docstatus, description, is_sub_contracted_item, stock_uom, default_bom, 
			last_purchase_rate, standard_rate, is_manufactured_item 
			from `tabItem` where name=%s""", item_code, as_dict = 1)

		return item
		
	def validate_rm_item(self, item):
		if item[0]['name'] == self.doc.item:
			msgprint("Item_code: %s in materials tab cannot be same as FG Item", 
				item[0]['name'], raise_exception=1)
		
		if not item or item[0]['docstatus'] == 2:
			msgprint("Item %s does not exist in system" % item[0]['item_code'], raise_exception = 1)
			
	def set_bom_material_details(self):
		for item in self.doclist.get({"parentfield": "bom_materials"}):
			ret = self.get_bom_material_detail({"item_code": item.item_code, "bom_no": item.bom_no, 
				"qty": item.qty})

			for r in ret:
				if not item.fields.get(r):
					item.fields[r] = ret[r]
		
	def get_bom_material_detail(self, args=None):
		""" Get raw material details like uom, desc and rate"""
		if not args:
			args = webnotes.form_dict.get('args')
		
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
			if self.doc.rm_cost_as_per == 'Valuation Rate':
				rate = self.get_valuation_rate(arg)
			elif self.doc.rm_cost_as_per == 'Last Purchase Rate':
				rate = arg['last_purchase_rate']
			elif self.doc.rm_cost_as_per == "Price List":
				if not self.doc.buying_price_list:
					webnotes.throw(_("Please select Price List"))
				rate = webnotes.conn.get_value("Item Price", {"price_list": self.doc.buying_price_list, 
					"item_code": arg["item_code"]}, "ref_rate") or 0
			elif self.doc.rm_cost_as_per == 'Standard Rate':
				rate = arg['standard_rate']

		return rate
		
	def update_cost(self):
		for d in self.doclist.get({"parentfield": "bom_materials"}):
			d.rate = self.get_bom_material_detail({
				'item_code': d.item_code, 
				'bom_no': d.bom_no,
				'qty': d.qty
			})["rate"]
		
		if self.doc.docstatus == 0:
			webnotes.bean(self.doclist).save()
		elif self.doc.docstatus == 1:
			self.calculate_cost()
			self.update_exploded_items()
			webnotes.bean(self.doclist).update_after_submit()

	def get_bom_unitcost(self, bom_no):
		bom = webnotes.conn.sql("""select name, total_cost/quantity as unit_cost from `tabBOM`
			where is_active = 1 and name = %s""", bom_no, as_dict=1)
		return bom and bom[0]['unit_cost'] or 0

	def get_valuation_rate(self, args):
		""" Get average valuation rate of relevant warehouses 
			as per valuation method (MAR/FIFO) 
			as on costing date	
		"""
		from stock.utils import get_incoming_rate
		dt = self.doc.costing_date or nowdate()
		time = self.doc.costing_date == nowdate() and now().split()[1] or '23:59'
		warehouse = webnotes.conn.sql("select warehouse from `tabBin` where item_code = %s", args['item_code'])
		rate = []
		for wh in warehouse:
			r = get_incoming_rate({
				"item_code": args.get("item_code"),
				"warehouse": wh[0],
				"posting_date": dt,
				"posting_time": time,
				"qty": args.get("qty") or 0
			})
			if r:
				rate.append(r)

		return rate and flt(sum(rate))/len(rate) or 0

	def manage_default_bom(self):
		""" Uncheck others if current one is selected as default, 
			update default bom in item master
		"""
		if self.doc.is_default and self.doc.is_active:
			from webnotes.model.utils import set_default
			set_default(self.doc, "item")
			webnotes.conn.set_value("Item", self.doc.item, "default_bom", self.doc.name)
		
		else:
			if not self.doc.is_active:
				webnotes.conn.set(self.doc, "is_default", 0)
			
			webnotes.conn.sql("update `tabItem` set default_bom = null where name = %s and default_bom = %s", 
				 (self.doc.item, self.doc.name))

	def clear_operations(self):
		if not self.doc.with_operations:
			self.doclist = self.doc.clear_table(self.doclist, 'bom_operations')
			for d in self.doclist.get({"parentfield": "bom_materials"}):
				d.operation_no = None

	def validate_main_item(self):
		""" Validate main FG item"""
		item = self.get_item_det(self.doc.item)
		if not item:
			msgprint("Item %s does not exists in the system or expired." % 
				self.doc.item, raise_exception = 1)
		elif item[0]['is_manufactured_item'] != 'Yes' \
				and item[0]['is_sub_contracted_item'] != 'Yes':
			msgprint("""As Item: %s is not a manufactured / sub-contracted item, \
				you can not make BOM for it""" % self.doc.item, raise_exception = 1)
		else:
			ret = webnotes.conn.get_value("Item", self.doc.item, ["description", "stock_uom"])
			self.doc.description = ret[0]
			self.doc.uom = ret[1]

	def validate_operations(self):
		""" Check duplicate operation no"""
		self.op = []
		for d in getlist(self.doclist, 'bom_operations'):
			if cstr(d.operation_no) in self.op:
				msgprint("Operation no: %s is repeated in Operations Table" % 
					d.operation_no, raise_exception=1)
			else:
				# add operation in op list
				self.op.append(cstr(d.operation_no))

	def validate_materials(self):
		""" Validate raw material entries """
		check_list = []
		for m in getlist(self.doclist, 'bom_materials'):
			# check if operation no not in op table
			if self.doc.with_operations and cstr(m.operation_no) not in self.op:
				msgprint("""Operation no: %s against item: %s at row no: %s \
					is not present at Operations table""" % 
					(m.operation_no, m.item_code, m.idx), raise_exception = 1)
			
			item = self.get_item_det(m.item_code)
			if item[0]['is_manufactured_item'] == 'Yes':
				if not m.bom_no:
					msgprint("Please enter BOM No aginst item: %s at row no: %s" % 
						(m.item_code, m.idx), raise_exception=1)
				else:
					self.validate_bom_no(m.item_code, m.bom_no, m.idx)

			elif m.bom_no:
				msgprint("""As Item %s is not a manufactured / sub-contracted item, \
					you can not enter BOM against it (Row No: %s).""" % 
					(m.item_code, m.idx), raise_exception = 1)

			if flt(m.qty) <= 0:
				msgprint("Please enter qty against raw material: %s at row no: %s" % 
					(m.item_code, m.idx), raise_exception = 1)

			self.check_if_item_repeated(m.item_code, m.operation_no, check_list)

	def validate_bom_no(self, item, bom_no, idx):
		"""Validate BOM No of sub-contracted items"""
		bom = webnotes.conn.sql("""select name from `tabBOM` where name = %s and item = %s 
			and is_active=1 and docstatus=1""", 
			(bom_no, item), as_dict =1)
		if not bom:
			msgprint("""Incorrect BOM No: %s against item: %s at row no: %s.
				It may be inactive or not submitted or does not belong to this item.""" % 
				(bom_no, item, idx), raise_exception = 1)

	def check_if_item_repeated(self, item, op, check_list):
		if [cstr(item), cstr(op)] in check_list:
			msgprint(_("Item") + " %s " % (item,) + _("has been entered atleast twice")
				+ (cstr(op) and _(" against same operation") or ""), raise_exception=1)
		else:
			check_list.append([cstr(item), cstr(op)])

	def check_recursion(self):
		""" Check whether recursion occurs in any bom"""

		check_list = [['parent', 'bom_no', 'parent'], ['bom_no', 'parent', 'child']]
		for d in check_list:
			bom_list, count = [self.doc.name], 0
			while (len(bom_list) > count ):
				boms = webnotes.conn.sql(" select %s from `tabBOM Item` where %s = '%s' " % 
					(d[0], d[1], cstr(bom_list[count])))
				count = count + 1
				for b in boms:
					if b[0] == self.doc.name:
						msgprint("""Recursion Occured => '%s' cannot be '%s' of '%s'.
							""" % (cstr(b[0]), cstr(d[2]), self.doc.name), raise_exception = 1)
					if b[0]:
						bom_list.append(b[0])
	
	def update_cost_and_exploded_items(self, bom_list=[]):
		bom_list = self.traverse_tree(bom_list)
		for bom in bom_list:
			bom_obj = get_obj("BOM", bom, with_children=1)
			bom_obj.on_update()
			
		return bom_list
			
	def traverse_tree(self, bom_list=[]):
		def _get_children(bom_no):
			return [cstr(d[0]) for d in webnotes.conn.sql("""select bom_no from `tabBOM Item` 
				where parent = %s and ifnull(bom_no, '') != ''""", bom_no)]
				
		count = 0
		if self.doc.name not in bom_list:
			bom_list.append(self.doc.name)
		
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
		self.doc.total_cost = self.doc.raw_material_cost + self.doc.operating_cost

	def calculate_op_cost(self):
		"""Update workstation rate and calculates totals"""
		total_op_cost = 0
		for d in getlist(self.doclist, 'bom_operations'):
			if d.workstation and not d.hour_rate:
				d.hour_rate = webnotes.conn.get_value("Workstation", d.workstation, "hour_rate")
			if d.hour_rate and d.time_in_mins:
				d.operating_cost = flt(d.hour_rate) * flt(d.time_in_mins) / 60.0
			total_op_cost += flt(d.operating_cost)
		self.doc.operating_cost = total_op_cost
		
	def calculate_rm_cost(self):
		"""Fetch RM rate as per today's valuation rate and calculate totals"""
		total_rm_cost = 0
		for d in getlist(self.doclist, 'bom_materials'):
			if d.bom_no:
				d.rate = self.get_bom_unitcost(d.bom_no)
			d.amount = flt(d.rate) * flt(d.qty)
			d.qty_consumed_per_unit = flt(d.qty) / flt(self.doc.quantity)
			total_rm_cost += d.amount
			
		self.doc.raw_material_cost = total_rm_cost

	def update_exploded_items(self):
		""" Update Flat BOM, following will be correct data"""
		self.get_exploded_items()
		self.add_exploded_items()

	def get_exploded_items(self):
		""" Get all raw materials including items from child bom"""
		self.cur_exploded_items = {}
		for d in getlist(self.doclist, 'bom_materials'):
			if d.bom_no:
				self.get_child_exploded_items(d.bom_no, d.qty)
			else:
				self.add_to_cur_exploded_items(webnotes._dict({
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
		
		child_fb_items = webnotes.conn.sql("""select item_code, description, stock_uom, qty, rate, 
			qty_consumed_per_unit from `tabBOM Explosion Item` 
			where parent = %s and docstatus = 1""", bom_no, as_dict = 1)
			
		for d in child_fb_items:
			self.add_to_cur_exploded_items(webnotes._dict({
				'item_code'				: d['item_code'], 
				'description'			: d['description'], 
				'stock_uom'				: d['stock_uom'], 
				'qty'					: flt(d['qty_consumed_per_unit'])*qty,
				'rate'					: flt(d['rate']),
			}))

	def add_exploded_items(self):
		"Add items to Flat BOM table"
		self.doclist = self.doc.clear_table(self.doclist, 'flat_bom_details', 1)
		for d in self.cur_exploded_items:
			ch = addchild(self.doc, 'flat_bom_details', 'BOM Explosion Item', self.doclist)
			for i in self.cur_exploded_items[d].keys():
				ch.fields[i] = self.cur_exploded_items[d][i]
			ch.amount = flt(ch.qty) * flt(ch.rate)
			ch.qty_consumed_per_unit = flt(ch.qty) / flt(self.doc.quantity)
			ch.docstatus = self.doc.docstatus
			ch.save(1)

	def get_parent_bom_list(self, bom_no):
		p_bom = webnotes.conn.sql("select parent from `tabBOM Item` where bom_no = '%s'" % bom_no)
		return p_bom and [i[0] for i in p_bom] or []

	def validate_bom_links(self):
		if not self.doc.is_active:
			act_pbom = webnotes.conn.sql("""select distinct bom_item.parent from `tabBOM Item` bom_item
				where bom_item.bom_no = %s and bom_item.docstatus = 1
				and exists (select * from `tabBOM` where name = bom_item.parent
					and docstatus = 1 and is_active = 1)""", self.doc.name)

			if act_pbom and act_pbom[0][0]:
				action = self.doc.docstatus < 2 and _("deactivate") or _("cancel")
				msgprint(_("Cannot ") + action + _(": It is linked to other active BOM(s)"),
					raise_exception=1)

def get_bom_items_as_dict(bom, qty=1, fetch_exploded=1):
	item_dict = {}
		
	query = """select 
				bom_item.item_code,
				item.item_name,
				ifnull(sum(bom_item.qty_consumed_per_unit),0) * %(qty)s as qty, 
				item.description, 
				item.stock_uom,
				item.default_warehouse,
				item.purchase_account as expense_account,
				item.cost_center
			from 
				`tab%(table)s` bom_item, `tabItem` item 
			where 
				bom_item.docstatus < 2 
				and bom_item.parent = "%(bom)s"
				and item.name = bom_item.item_code 
				%(conditions)s
				group by item_code, stock_uom"""
	
	if fetch_exploded:
		items = webnotes.conn.sql(query % {
			"qty": qty,
			"table": "BOM Explosion Item",
			"bom": bom,
			"conditions": """and ifnull(item.is_pro_applicable, 'No') = 'No'
					and ifnull(item.is_sub_contracted_item, 'No') = 'No' """
		}, as_dict=True)
	else:
		items = webnotes.conn.sql(query % {
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

@webnotes.whitelist()
def get_bom_items(bom, qty=1, fetch_exploded=1):
	items = get_bom_items_as_dict(bom, qty, fetch_exploded).values()
	items.sort(lambda a, b: a.item_code > b.item_code and 1 or -1)
	return items
