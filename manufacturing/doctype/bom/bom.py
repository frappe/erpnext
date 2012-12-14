# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cint, cstr, flt, now, nowdate
from webnotes.model.doc import Document, addchild
from webnotes.model.wrapper import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint

sql = webnotes.conn.sql


class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def autoname(self):
		last_name = sql("""select max(name) from `tabBOM` 
			where name like 'BOM/%s/%%'""" % self.doc.item)
		if last_name:
			idx = cint(cstr(last_name[0][0]).split('/')[-1]) + 1
		else:
			idx = 1
		self.doc.name = 'BOM/' + self.doc.item + ('/%.3i' % idx)


	def get_item_det(self, item_code):
		item = sql("""select name, is_asset_item, is_purchase_item, docstatus,
		 	is_sub_contracted_item, stock_uom, default_bom, 
			last_purchase_rate, standard_rate, is_manufactured_item 
			from `tabItem` where item_code = %s""", item_code, as_dict = 1)

		return item


	def get_item_detail(self, item_code):
		return { 'uom' : webnotes.conn.get_value("Item", item_code, "stock_uom")}

	def get_workstation_details(self,workstation):
		return {'hour_rate': webnotes.conn.get_value("Workstation", workstation, "hour_rate")}


	def validate_rm_item(self, item):
		if item[0]['name'] == self.doc.item:
			msgprint("Item_code: %s in materials tab cannot be same as FG Item", 
				item[0]['name'], raise_exception=1)
		
		if item and item[0]['is_asset_item'] == 'Yes':
			msgprint("Item: %s is an asset item, please check", item[0]['name'], raise_exception=1)

		if not item or item[0]['docstatus'] == 2:
			msgprint("Item %s does not exist in system" % item[0]['item_code'], raise_exception = 1)


	def get_bom_material_detail(self):
		""" Get raw material details like uom, desc and rate"""

		arg = webnotes.form_dict.get('args')
		import json
		arg = json.loads(arg)
		
		item = self.get_item_det(arg['item_code'])
		self.validate_rm_item(item)
		
		arg['bom_no'] = arg['bom_no'] or item and cstr(item[0]['default_bom']) or ''
		arg.update(item[0])

		rate = self.get_rm_rate(arg)
		ret_item = {
			 'description'  : item and arg['description'] or '',
			 'stock_uom'	: item and arg['stock_uom'] or '',
			 'bom_no'		: arg['bom_no'],
			 'rate'			: rate
		}
		return ret_item


	def get_rm_rate(self, arg):
		"""	Get raw material rate as per selected method, if bom exists takes bom cost """

		if arg['bom_no']:
			rate = self.get_bom_unitcost(arg['bom_no'])
		elif arg and (arg['is_purchase_item'] == 'Yes' or arg['is_sub_contracted_item'] == 'Yes'):
			if self.doc.rm_cost_as_per == 'Valuation Rate':
				rate = self.get_valuation_rate(arg)
			elif self.doc.rm_cost_as_per == 'Last Purchase Rate':
				rate = arg['last_purchase_rate']
			elif self.doc.rm_cost_as_per == 'Standard Rate':
				rate = arg['standard_rate']

		return rate

	def get_bom_unitcost(self, bom_no):
		bom = sql("""select name, total_cost/quantity as unit_cost from `tabBOM`
			where is_active = 1 and name = %s""", bom_no, as_dict=1)
		return bom and bom[0]['unit_cost'] or 0

	def get_valuation_rate(self, arg):
		""" Get average valuation rate of relevant warehouses 
			as per valuation method (MAR/FIFO) 
			as on costing date	
		"""
		dt = self.doc.costing_date or nowdate()
		time = self.doc.costing_date == nowdate() and now().split()[1] or '23:59'
		warehouse = sql("select warehouse from `tabBin` where item_code = %s", arg['item_code'])
		rate = []
		for wh in warehouse:
			r = get_obj('Valuation Control').get_incoming_rate(dt, time, 
				arg['item_code'], wh[0], qty=arg.get('qty', 0))
			if r:
				rate.append(r)

		return rate and flt(sum(rate))/len(rate) or 0


	def manage_default_bom(self):
		""" Uncheck others if current one is selected as default, 
			update default bom in item master
		"""

		if self.doc.is_default and self.doc.is_active:
			sql("update `tabBOM` set is_default = 0 where name != %s and item=%s", 
				(self.doc.name, self.doc.item))

			webnotes.conn.set_value("Item", self.doc.item, "default_bom", self.doc.name)
		else:
			sql("update `tabItem` set default_bom = '' where name = %s and default_bom = %s", 
			 	(self.doc.item, self.doc.name))


	def validate(self):
		self.validate_main_item()
		self.validate_operations()
		self.validate_materials()

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
			if self.doc.track_operations and cstr(m.operation_no) not in self.op:
				msgprint("""Operation no: %s against item: %s at row no: %s \
					is not present at Operations table""" % 
					(m.operation_no, m.item_code, m.idx), raise_exception = 1)
		
			item = self.get_item_det(m.item_code)
			if item[0]['is_manufactured_item'] == 'Yes' or \
					item[0]['is_sub_contracted_item'] == 'Yes':
				if not m.bom_no:
					msgprint("Please enter BOM No aginst item: %s at row no: %s" % 
						(m.item_code, m.idx), raise_exception=1)
				else:
					self.validate_bom_no(m.item_code, m.bom_no, m.idx)

			elif m.bom_no:
				msgprint("""As Item %s is not a manufactured / sub-contracted item, \
					you can enter BOM against it (Row No: %s).""" % 
					(m.item_code, m.idx), raise_exception = 1)

			if flt(m.qty) <= 0:
				msgprint("Please enter qty against raw material: %s at row no: %s" % 
					(m.item_code, m.idx), raise_exception = 1)

			self.check_if_item_repeated(m.item_code, m.operation_no, check_list)


	def validate_bom_no(self, item, bom_no, idx):
		"""Validate BOM No of sub-contracted items"""
		bom = sql("""select name from `tabBOM` where name = %s and item = %s 
			and is_active = 1 and docstatus < 2 """, 
			(bom_no, item), as_dict =1)
		if not bom:
			msgprint("""Incorrect BOM No: %s against item: %s at row no: %s.
				It may be inactive or cancelled or for some other item.""" % 
				(bom_no, item, idx), raise_exception = 1)


	def check_if_item_repeated(self, item, op, check_list):
		if [cstr(item), cstr(op)] in check_list:
			msgprint("Item %s has been entered twice against same operation" % 
				item, raise_exception = 1)
		else:
			check_list.append([cstr(item), cstr(op)])


	def on_update(self):
		self.check_recursion()
		self.update_cost_and_exploded_items()

	def check_recursion(self):
		""" Check whether recursion occurs in any bom"""

		check_list = [['parent', 'bom_no', 'parent'], ['bom_no', 'parent', 'child']]
		for d in check_list:
			bom_list, count = [self.doc.name], 0
			while (len(bom_list) > count ):
				boms = sql(" select %s from `tabBOM Item` where %s = '%s' " % 
					(d[0], d[1], cstr(bom_list[count])))
				count = count + 1
				for b in boms:
					if b[0] == self.doc.name:
						msgprint("""Recursion Occured => '%s' cannot be '%s' of '%s'.
							""" % (cstr(b), cstr(d[2]), self.doc.name), raise_exception = 1)
					if b[0]:
						bom_list.append(b[0])
						
	
	def update_cost_and_exploded_items(self, calculate_cost=True):
		bom_list = self.traverse_tree()
		bom_list.reverse()
		for bom in bom_list:
			bom_obj = get_obj("BOM", bom, with_children=1)
			if calculate_cost:
				bom_obj.calculate_cost()
			bom_obj.update_flat_bom()
			

	def traverse_tree(self):
		def _get_childs(bom_no):
			return [cstr(d[0]) for d in webnotes.conn.sql("""select bom_no from `tabBOM Item` 
				where parent = %s and ifnull(bom_no, '') != ''""", bom_no)]
				
		bom_list, count = [self.doc.name], 0		
		while(count < len(bom_list)):
			for child_bom in _get_childs(bom_list[count]):
				if child_bom not in bom_list:
					bom_list.append(child_bom)
			count += 1
		return bom_list
	
	
	def calculate_cost(self):
		"""Calculate bom totals"""
		self.calculate_op_cost()
		self.calculate_rm_cost()
		self.doc.total_cost = self.doc.raw_material_cost + self.doc.operating_cost
		self.doc.modified = now()
		self.doc.save()
	

	def calculate_op_cost(self):
		"""Update workstation rate and calculates totals"""
		total_op_cost = 0
		for d in getlist(self.doclist, 'bom_operations'):
			if d.hour_rate and d.time_in_mins:
				d.operating_cost = flt(d.hour_rate) * flt(d.time_in_mins) / 60.0
			d.save()
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
			d.save()
			total_rm_cost += d.amount
		self.doc.raw_material_cost = total_rm_cost


	def update_flat_bom(self):
		""" Update Flat BOM, following will be correct data"""
		self.get_flat_bom_items()
		self.add_to_flat_bom_detail()


	def get_flat_bom_items(self):
		""" Get all raw materials including items from child bom"""
		self.cur_flat_bom_items = []
		for d in getlist(self.doclist, 'bom_materials'):
			if d.bom_no:
				self.get_child_flat_bom_items(d.bom_no, d.qty)
			else:
				self.cur_flat_bom_items.append({
					'item_code'				: d.item_code, 
					'description'			: d.description, 
					'stock_uom'				: d.stock_uom, 
					'qty'					: flt(d.qty),
					'rate'					: flt(d.rate), 
					'amount'				: flt(d.amount),
					'parent_bom'			: d.parent,
					'mat_detail_no'			: d.name,
					'qty_consumed_per_unit' : flt(d.qty_consumed_per_unit)
				})
	
	
	def get_child_flat_bom_items(self, bom_no, qty):
		""" Add all items from Flat BOM of child BOM"""
		
		child_fb_items = sql("""select item_code, description, stock_uom, qty, rate, 
			amount, parent_bom, mat_detail_no, qty_consumed_per_unit 
			from `tabBOM Explosion Item` where parent = '%s' and docstatus = 1""" %
			bom_no, as_dict = 1)
		for d in child_fb_items:
			self.cur_flat_bom_items.append({
				'item_code'				: d['item_code'], 
				'description'			: d['description'], 
				'stock_uom'				: d['stock_uom'], 
				'qty'					: flt(d['qty_consumed_per_unit'])*qty,
				'rate'					: flt(d['rate']), 
				'amount'				: flt(d['amount']),
				'parent_bom'			: d['parent_bom'],
				'mat_detail_no'			: d['mat_detail_no'],
				'qty_consumed_per_unit' : flt(d['qty_consumed_per_unit'])*qty/flt(self.doc.quantity)

			})

	def add_to_flat_bom_detail(self):
		"Add items to Flat BOM table"
		self.doclist = self.doc.clear_table(self.doclist, 'flat_bom_details', 1)
		for d in self.cur_flat_bom_items:
			ch = addchild(self.doc, 'flat_bom_details', 'BOM Explosion Item', 1, self.doclist)
			for i in d.keys():
				ch.fields[i] = d[i]
			ch.docstatus = self.doc.docstatus
			ch.save(1)
		self.doc.save()


	def get_parent_bom_list(self, bom_no):
		p_bom = sql("select parent from `tabBOM Item` where bom_no = '%s'" % bom_no)
		return p_bom and [i[0] for i in p_bom] or []


	def on_submit(self):
		self.manage_default_bom()


	def on_cancel(self):
		# check if used in any other bom
		par = sql("""select t1.parent from `tabBOM Item` t1, `tabBOM` t2 
			where t1.parent = t2.name and t1.bom_no = %s and t1.docstatus = 1 
			and t2.is_active = 1""", self.doc.name)
		if par:
			msgprint("""BOM can not be cancelled, as it is a child item \
				in following active BOM %s""" % [d[0] for d in par], raise_exception=1)
			
		webnotes.conn.set(self.doc, "is_active", 0)
		webnotes.conn.set(self.doc, "is_default", 0)
		self.manage_default_bom()
		self.update_cost_and_exploded_items(calculate_cost=False)
				

	def on_update_after_submit(self):
		self.manage_default_bom()
		self.validate_inactive_bom()
	
	
	def validate_inactive_bom(self):
		if not self.doc.is_active:
			act_pbom = sql("""select distinct t1.parent from `tabBOM Item` t1, `tabBOM` t2 
				where t1.bom_no =%s and t2.name = t1.parent and t2.is_active = 1 
				and t2.docstatus = 1 and t1.docstatus =1 """, self.doc.name)
			if act_pbom and act_pbom[0][0]:
				msgprint("""Sorry cannot inactivate as BOM: %s is child 
					of one or many other active parent BOMs""" % self.doc.name, raise_exception=1)