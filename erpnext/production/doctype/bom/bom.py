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

import webnotes
from webnotes.utils import cint, cstr, flt, get_defaults, getdate, now, nowdate
from webnotes.model.doc import Document, addchild, getchildren, make_autoname
from webnotes.model.doclist import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value

# -----------------------------------------------------------------------------------------

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist

	def autoname(self):
		last_name = sql("select max(name) from `tabBOM` where name like 'BOM/%s/%%'" % self.doc.item)
		if last_name:
			idx = cint(cstr(last_name[0][0]).split('/')[-1]) + 1
		else:
			idx = 1
		self.doc.name = 'BOM/' + self.doc.item + ('/%.3i' % idx)


	def get_item_det(self, item_code):
		item = sql("""select name, is_asset_item, is_purchase_item, docstatus, is_sub_contracted_item,
			description, stock_uom, default_bom, last_purchase_rate, standard_rate, is_manufactured_item from `tabItem` 
			where item_code = %s""", item_code, as_dict = 1)

		return item


	def get_item_detail(self, item_code):
		""" Get stock uom and description for finished good item"""

		item = self.get_item_det(item_code)
		ret={
			'description'	 : item and item[0]['description'] or '',
			'uom'				: item and item[0]['stock_uom'] or ''
		}
		return ret



	def get_workstation_details(self,workstation):
		""" Fetch hour rate from workstation master"""

		ws = sql("select hour_rate from `tabWorkstation` where name = %s",workstation , as_dict = 1)
		ret = {
			'hour_rate'				: ws and flt(ws[0]['hour_rate']) or '',
		}
		return ret



	def validate_rm_item(self, item):
		""" Validate raw material items"""

		if item[0]['name'] == self.doc.item:
			msgprint(" Item_code: "+item[0]['name']+" in materials tab cannot be same as FG Item in BOM := " +cstr(self.doc.name), raise_exception=1)
		
		if item and item[0]['is_asset_item'] == 'Yes':
			msgprint("Sorry!!! Item " + item[0]['name'] + " is an Asset of the company. Entered in BOM => " + cstr(self.doc.name), raise_exception = 1)

		if not item or item[0]['docstatus'] == 2:
			msgprint("Item %s does not exist in system" % item[0]['item_code'], raise_exception = 1)



	def get_bom_material_detail(self, arg):
		""" Get raw material details like uom, desc and rate"""

		arg = eval(arg)
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
			bom = sql("""select name, total_cost/quantity as unit_cost from `tabBOM`
				where is_active = 'Yes' and name = %s""", arg['bom_no'], as_dict=1)
			rate = bom and bom[0]['unit_cost'] or 0
		elif arg and (arg['is_purchase_item'] == 'Yes' or arg['is_sub_contracted_item'] == 'Yes'):
			if self.doc.rm_cost_as_per == 'Valuation Rate':
				rate = self.get_valuation_rate(arg)
			elif self.doc.rm_cost_as_per == 'Last Purchase Rate':
				rate = arg['last_purchase_rate']
			elif self.doc.rm_cost_as_per == 'Standard Rate':
				rate = arg['standard_rate']

		return rate

	

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
			r = get_obj('Valuation Control').get_incoming_rate(dt, time, arg['item_code'], wh[0], qty = arg.get('qty', 0))
			if r:
				rate.append(r)

		return rate and flt(sum(rate))/len(rate) or 0



	def manage_default_bom(self):
		""" Uncheck others if current one is selected as default, update default bom in item master"""

		if self.doc.is_default and self.doc.is_active == 'Yes':
			sql("update `tabBOM` set is_default = 0 where name != %s and item=%s", (self.doc.name, self.doc.item))

			# update default bom in Item Master
			sql("update `tabItem` set default_bom = %s where name = %s", (self.doc.name, self.doc.item))
		else:
			sql("update `tabItem` set default_bom = '' where name = %s and default_bom = %s", (self.doc.item, self.doc.name))
	


	def manage_active_bom(self):
		""" Manage active/inactive """
		if self.doc.is_active == 'Yes':
			self.validate()
		else:
			self.check_active_parent_boms()



	def check_active_parent_boms(self):
		""" Check parent BOM before making it inactive """
		act_pbom = sql("""select distinct t1.parent from `tabBOM Item` t1, `tabBOM` t2 
			where t1.bom_no =%s and t2.name = t1.parent and t2.is_active = 'Yes' 
			and t2.docstatus = 1 and t1.docstatus =1 """, self.doc.name)
		if act_pbom and act_pbom[0][0]:
			msgprint("""Sorry cannot inactivate as BOM: %s is child 
				of one or many other active parent BOMs""" % self.doc.name, raise_exception=1)



	def calculate_cost(self):
		"""Calculate bom totals"""
		self.doc.costing_date = nowdate()
		self.calculate_op_cost()
		self.calculate_rm_cost()
		self.doc.total_cost = self.doc.raw_material_cost + self.doc.operating_cost
		self.doc.modified = now()
		self.doc.save()

		self.update_flat_bom_engine(is_submit = self.doc.docstatus)

	

	def calculate_op_cost(self):
		"""Update workstation rate and calculates totals"""
		total_op_cost = 0
		for d in getlist(self.doclist, 'bom_operations'):
			hour_rate = sql("select hour_rate from `tabWorkstation` where name = %s", cstr(d.workstation))
			d.hour_rate = hour_rate and flt(hour_rate[0][0]) or 0
			d.operating_cost = flt(d.hour_rate) * flt(d.time_in_mins) / 60
			total_op_cost += d.operating_cost
		self.doc.operating_cost = total_op_cost



	def calculate_rm_cost(self):
		"""Fetch RM rate as per today's valuation rate and calculate totals"""
		total_rm_cost = 0
		for d in getlist(self.doclist, 'bom_materials'):
			#if self.doc.rm_cost_as_per == 'Valuation Rate':
			arg = {'item_code': d.item_code, 'qty': d.qty, 'bom_no': d.bom_no}
			ret = self.get_bom_material_detail(cstr(arg))
			for k in ret:
				d.fields[k] = ret[k]

			d.amount = flt(d.rate) * flt(d.qty)
			total_rm_cost += d.amount
		self.doc.raw_material_cost = total_rm_cost



	def validate_main_item(self):
		""" Validate main FG item"""
		item = self.get_item_det(self.doc.item)
		if not item:
			msgprint("Item %s does not exists in the system or expired." % self.doc.item, raise_exception = 1)

		elif item[0]['is_manufactured_item'] != 'Yes' and item[0]['is_sub_contracted_item'] != 'Yes':
			msgprint("""As Item: %s is not a manufactured / sub-contracted item, 
				you can not make BOM for it""" % self.doc.item, raise_exception = 1)



	def validate_operations(self):
		""" Check duplicate operation no"""
		self.op = []
		for d in getlist(self.doclist, 'bom_operations'):
			if cstr(d.operation_no) in self.op:
				msgprint("Operation no: %s is repeated in Operations Table"% d.operation_no, raise_exception=1)
			else:
				# add operation in op list
				self.op.append(cstr(d.operation_no))



	def validate_materials(self):
		""" Validate raw material entries """
		check_list = []
		for m in getlist(self.doclist, 'bom_materials'):
			# check if operation no not in op table
			if m.operation_no not in self.op:
				msgprint("""Operation no: %s against item: %s at row no: %s is not present 
					at Operations table"""% (m.operation_no, m.item_code, m.idx), raise_exception = 1)
		
			item = self.get_item_det(m.item_code)
			if item[0]['is_manufactured_item'] == 'Yes' or item[0]['is_sub_contracted_item'] == 'Yes':
				if not m.bom_no:
					msgprint("Please enter BOM No aginst item: %s at row no: %s"% (m.item_code, m.idx), raise_exception=1)
				else:
					self.validate_bom_no(m.item_code, m.bom_no, m.idx)

			elif m.bom_no:
				msgprint("""As Item %s is not a manufactured / sub-contracted item, 
					you can enter BOM against it (Row No: %s)."""% (m.item_code, m.idx), raise_excepiton = 1)

			if flt(m.qty) <= 0:
				msgprint("Please enter qty against raw material: %s at row no: %s"% (m.item_code, m.idx), raise_exception = 1)

			self.check_if_item_repeated(m.item_code, m.operation_no, check_list)



	def validate_bom_no(self, item, bom_no, idx):
		"""Validate BOM No of sub-contracted items"""
		bom = sql("""select name from `tabBOM` where name = %s and item = %s 
			and ifnull(is_active, 'No') = 'Yes'	and docstatus < 2 """, (bom_no, item), as_dict =1)
		if not bom:
			msgprint("""Incorrect BOM No: %s against item: %s at row no: %s.
				It may be inactive or cancelled or for some other item."""% (bom_no, item, idx), raise_exception = 1)
				


	def check_if_item_repeated(self, item, op, check_list):
		if [cstr(item), cstr(op)] in check_list:
			msgprint("Item %s has been entered twice against same operation" % item, raise_exception = 1)
		else:
			check_list.append([cstr(item), cstr(op)])



	#----- Document on Save function------
	def validate(self):
		self.validate_main_item()
		self.validate_operations()
		self.validate_materials()
		self.validate_operations()



	def check_recursion(self):
		""" Check whether reqursion occurs in any bom"""

		check_list = [['parent', 'bom_no', 'parent'], ['bom_no', 'parent', 'child']]
		for d in check_list:
			bom_list, count = [self.doc.name], 0
			while (len(bom_list) > count ):
				boms = sql(" select %s from `tabBOM Item` where %s = '%s' " % (d[0], d[1], cstr(bom_list[count])))
				count = count + 1
				for b in boms:
					if b[0] == self.doc.name:
						msgprint("""Recursion Occured => '%s' cannot be '%s' of '%s'.
							""" % (cstr(b), cstr(d[2]), self.doc.name), raise_exception = 1)
					if b[0]:
						bom_list.append(b[0])



	def on_update(self):
		self.check_recursion()



	def add_to_flat_bom_detail(self, is_submit = 0):
		"Add items to Flat BOM table"
		self.doclist = self.doc.clear_table(self.doclist, 'flat_bom_details', 1)
		for d in self.cur_flat_bom_items:
			ch = addchild(self.doc, 'flat_bom_details', 'BOM Explosion Item', 1, self.doclist)
			for i in d.keys():
				ch.fields[i] = d[i]
			ch.docstatus = is_submit
			ch.save(1)
		self.doc.save()



	def get_child_flat_bom_items(self, bom_no, qty):
		""" Add all items from Flat BOM of child BOM"""

		child_fb_items = sql("""select item_code, description, stock_uom, qty, rate, amount, parent_bom, mat_detail_no, qty_consumed_per_unit 
			from `tabBOM Explosion Item` where parent = '%s' and docstatus = 1""" % bom_no, as_dict = 1)
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




	# Get Current Flat BOM Items
	# -----------------------------
	def get_current_flat_bom_items(self):
		""" Get all raw materials including items from child bom"""
		self.cur_flat_bom_items = []
		for d in getlist(self.doclist, 'bom_materials'):
			self.cur_flat_bom_items.append({
				'item_code'				: d.item_code, 
				'description'			: d.description, 
				'stock_uom'				: d.stock_uom, 
				'qty'					: flt(d.qty),
				'rate'					: flt(d.rate), 
				'amount'				: flt(d.amount),
				'parent_bom'			: d.parent, #item and item[0][0]=='No' and d.bom_no or d.parent, 
				'mat_detail_no'			: d.name,
				'qty_consumed_per_unit' : flt(d.qty_consumed_per_unit)
			})
			if d.bom_no:
				self.get_child_flat_bom_items(d.bom_no, d.qty)


	def update_flat_bom_engine(self, is_submit = 0):
		""" Update Flat BOM, following will be correct data"""
		self.get_current_flat_bom_items()
		self.add_to_flat_bom_detail(is_submit)


	def get_parent_bom_list(self, bom_no):
		p_bom = sql("select parent from `tabBOM Item` where bom_no = '%s'" % bom_no)
		return p_bom and [i[0] for i in p_bom] or []


	def on_submit(self):
		self.manage_default_bom()
		self.update_flat_bom_engine(1)


	def on_cancel(self):
		# check if used in any other bom
		par = sql("""select t1.parent from `tabBOM Item` t1, `tabBOM` t2 
			where t1.parent = t2.name and t1.bom_no = %s and t1.docstatus = 1 and t2.is_active = 'Yes'""", self.doc.name)
		if par:
			msgprint("BOM can not be cancelled, as it is a child item in following active BOM %s"% [d[0] for d in par])
			raise Exception
