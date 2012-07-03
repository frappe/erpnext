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
from webnotes.utils import cint, cstr, flt, getdate, now, nowdate
from webnotes.model.doc import addchild
from webnotes.model.doclist import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint, errprint

sql = webnotes.conn.sql
	
# -----------------------------------------------------------------------------------------


class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.item_dict = {}
		
	def get_item_details(self, item_code):
		""" Pull other item details from item master"""

		item = sql("""select description, stock_uom, default_bom from `tabItem` where name = %s 
			and (ifnull(end_of_life,'')='' or end_of_life = '0000-00-00' or end_of_life > now())""", item_code, as_dict =1 )
		ret = {
			'description'	: item and item[0]['description'],
			'stock_uom'		: item and item[0]['stock_uom'],
			'bom_no'		: item and item[0]['default_bom']
		}
		return ret
	

	def get_so_details(self, so):
		"""Pull other details from so"""
		so = sql("select transaction_date, customer, grand_total from `tabSales Order` where name = %s", so, as_dict = 1)
		ret = {
			'sales_order_date': so and so[0]['transaction_date'] or '',
			'customer' : so[0]['customer'] or '',
			'grand_total': so[0]['grand_total']
		}
		return ret


	def clear_so_table(self):
		""" Clears sales order table"""
		self.doclist = self.doc.clear_table(self.doclist, 'pp_so_details')



	def clear_item_table(self):
		""" Clears item table"""
		self.doclist = self.doc.clear_table(self.doclist, 'pp_details')



	def get_open_sales_orders(self):
		""" Pull sales orders  which are pending to deliver based on criteria selected"""
		cond = self.get_filter_condition()
		open_so = sql("""
			select 
				distinct t1.name, t1.transaction_date, t1.customer, t1.grand_total 
			from 
				`tabSales Order` t1, `tabSales Order Item` t2, `tabDelivery Note Packing Item` t3, tabItem t4
			where 
				t1.name = t2.parent and t1.name = t3.parent and t3.parenttype = 'Sales Order' and t1.docstatus = 1 and t2.item_code = t3.parent_item 
				and t4.name = t3.item_code and  t1.status != 'Stopped' and t1.company = '%s' and ifnull(t2.qty, 0) > ifnull(t2.delivered_qty, 0) 
				and (ifnull(t4.is_pro_applicable, 'No') = 'Yes' or ifnull(t4.is_sub_contracted_item, 'No') = 'Yes') %s
			order by t1.name desc
		"""% (self.doc.company, cond), as_dict = 1)

		self.add_so_in_table(open_so)



	def validate_company(self):
		if not self.doc.company:
			msgprint("Please enter Company", raise_exception=1)

		

	def get_filter_condition(self):
		self.validate_company()

		cond = ''
		if self.doc.from_date:
			cond += ' and t1.transaction_date >= "' + self.doc.from_date + '"'
		if self.doc.to_date:
			cond += ' and t1.transaction_date <= "' + self.doc.to_date + '"'
		if self.doc.customer:
			cond += ' and t1.customer = "' + self.doc.customer + '"'
		if self.doc.fg_item:
			cond += ' and t3.item_code = "' + self.doc.fg_item + '"'

		return cond



	def add_so_in_table(self, open_so):
		""" Add sales orders in the table"""
		so_list = []
		for d in getlist(self.doclist, 'pp_so_details'):
			so_list.append(d.sales_order)
		for r in open_so:
			if cstr(r['name']) not in so_list:
				pp_so = addchild(self.doc, 'pp_so_details', 'Production Plan Sales Order', 1, self.doclist)
				pp_so.sales_order = r['name']
				pp_so.sales_order_date = cstr(r['transaction_date'])
				pp_so.customer = cstr(r['customer'])
				pp_so.grand_total = flt(r['grand_total'])



	def get_items_from_so(self):
		""" Pull items from Sales Order, only proction item
			and subcontracted item will be pulled from Packing item 
			and add items in the table
		"""
		so = self.get_included_so()
		items = self.get_packing_items(so)
		self.add_items(items)


	def get_included_so(self):
		so = "'" + "','".join([cstr(d.sales_order) for d in getlist(self.doclist, 'pp_so_details') if d.include_in_plan]) + "'"
		return so



	def get_packing_items(self, so):
		packing_items = sql("""
			select 
				t0.name, t2.parent_item, t2.item_code, 
				(t1.qty - ifnull(t1.delivered_qty,0)) * (ifnull(t2.qty,0) / ifnull(t1.qty,1)) as 'pending_qty' 
			from
				`tabSales Order` t0, `tabSales Order Item` t1, `tabDelivery Note Packing Item` t2, `tabItem` t3
			where 
				t0.name = t1.parent and t0.name = t2.parent and t1.name = t2.parent_detail_docname
				and t0.name in (%s) and t0.docstatus = 1 and t1.qty > ifnull(t1.delivered_qty,0) and t3.name = t2.item_code 
				and (ifnull(t3.is_pro_applicable, 'No') = 'Yes' or ifnull(t3.is_sub_contracted_item, 'No') = 'Yes')
		""" % so, as_dict=1)
		return packing_items
		


	def add_items(self, packing_items):
		for d in getlist(self.doclist, 'pp_details'):
			if d.sales_order:
				d.parent = ''

		for p in packing_items:	
			item_details = sql("select description, stock_uom, default_bom from tabItem where name=%s", p['item_code'])
			pi = addchild(self.doc, 'pp_details', 'Production Plan Item', 1, self.doclist)
			pi.sales_order				= p['name']
			pi.parent_packing_item		= p['parent_item']
			pi.item_code				= p['item_code']
			pi.description				= item_details and item_details[0][0] or ''
			pi.stock_uom				= item_details and item_details[0][1] or ''
			pi.bom_no					= item_details and item_details[0][2] or ''
			pi.so_pending_qty			= flt(p['pending_qty'])
			pi.planned_qty				= flt(p['pending_qty'])
	


	def validate_data(self):
		for d in getlist(self.doclist, 'pp_details'):
			if not d.pro_created:
				self.validate_bom_no(d)

				if not flt(d.planned_qty):
					msgprint("Please Enter Planned Qty for item: %s at row no: %s"% (d.item_code, d.idx), raise_exception=1)
		return 'validated'

				

	def validate_bom_no(self, d):
		if not d.bom_no:
			msgprint("Please enter bom no for item: %s at row no: %s" % (d.item_code, d.idx), raise_exception=1)
		else:
			bom = sql("""select name from `tabBOM` where item = %s and docstatus = 1 
				and name = %s and ifnull(is_active, 'No') = 'Yes'""", (d.item_code, d.bom_no), as_dict = 1)
			if not bom:
				msgprint("""Incorrect BOM No: %s entered for item: %s at row no: %s
					May be BOM is inactive or for other item or does not exists in the system"""% (d.bom_no, d.item_doce, d.idx))



	def download_raw_materials(self):
		""" Create csv data for required raw material to produce finished goods"""
		bom_dict = self.get_distinct_bom(action = 'download_rm')
		self.get_raw_materials(bom_dict)
		return self.get_csv()



	
	def get_raw_materials(self, bom_dict):
		""" Get raw materials considering sub-assembly items """
		for bom in bom_dict:
			if self.doc.consider_sa_items == 'Yes':
				# Get all raw materials considering SA items as raw materials, 
				# so no childs of SA items
				fl_bom_items = sql("""
					select item_code, ifnull(sum(qty_consumed_per_unit), 0) * '%s', description, stock_uom 
					from `tabBOM Item` 
					where parent = '%s' and docstatus < 2 
					group by item_code
				""" % (flt(bom_dict[bom]), bom))

			else:
				# get all raw materials with sub assembly childs					
				fl_bom_items = sql("""
					select 
						item_code,ifnull(sum(qty_consumed_per_unit),0)*%s as qty, description, stock_uom
					from 
						( 
							select distinct fb.name, fb.description, fb.item_code, fb.qty_consumed_per_unit, fb.stock_uom 
							from `tabBOM Explosion Item` fb,`tabItem` it 
							where it.name = fb.item_code and ifnull(it.is_pro_applicable, 'No') = 'No'
							and ifnull(it.is_sub_contracted_item, 'No') = 'No' and fb.docstatus<2 and fb.parent=%s
						) a
					group by item_code,stock_uom
				""" , (flt(bom_dict[bom]), bom))
			
			self.make_items_dict(fl_bom_items)



	def make_items_dict(self, item_list):
		for i in item_list:
			self.item_dict[i[0]] = [(flt(self.item_dict.get(i[0], [0])[0]) + flt(i[1])), i[2], i[3]]


	def get_csv(self):
		item_list = [['Item Code', 'Description', 'Stock UOM', 'Required Qty', 'Warehouse', 'Quantity Requested for Purchase', 'Ordered Qty', 'Actual Qty']]
		for d in self.item_dict:
			item_list.append([d, self.item_dict[d][1], self.item_dict[d][2], self.item_dict[d][0]]),
			item_qty= sql("select warehouse, indented_qty, ordered_qty, actual_qty from `tabBin` where item_code = %s", d)
			i_qty, o_qty, a_qty = 0,0,0
			for w in item_qty:
				i_qty, o_qty, a_qty = i_qty + flt(w[1]), o_qty + flt(w[2]), a_qty + flt(w[3])
				item_list.append(['', '', '', '', w[0], flt(w[1]), flt(w[2]), flt(w[3])])
			if item_qty:
				item_list.append(['', '', '', '', 'Total', i_qty, o_qty, a_qty])

		return item_list
		


	def raise_production_order(self):
		"""It will raise production order (Draft) for all distinct FG items"""
		self.validate_company()
		self.validate_data()

		pp_items = self.get_distinct_bom(action = 'raise_pro_order')
		pro = get_obj(dt = 'Production Control').create_production_order(self.doc.company, pp_items)
		if pro:
			for d in getlist(self.doclist, 'pp_details'):
				d.is_pro_created = 1
			msgprint("Following Production Order has been generated:\n" + '\n'.join(pro))
		else :
			msgprint("No Production Order is generated.")



	def get_distinct_bom(self, action):
		""" Club similar BOM and item for processing"""

		bom_dict, item_dict, pp_items = {}, {}, []
		for d in getlist(self.doclist, 'pp_details'):
			if action == 'download_rm':
				bom_dict[d.bom_no] = bom_dict.get(d.bom_no, 0) + flt(d.planned_qty)
			elif not d.is_pro_created:
				item_dict[d.item_code] = [(item_dict.get(d.item_code, 0) + flt(d.planned_qty)), d.bom_no, d.description, d.stock_uom]

		if action == 'raise_pro_order':
			for d in item_dict:
				pp_items.append({
					'production_item'	: d, 
					'qty'				: item_dict[d][0],
					'bom_no'			: item_dict[d][1],
					'description'		: item_dict[d][2],
					'stock_uom'			: item_dict[d][3],
					'consider_sa_items' : self.doc.consider_sa_items
				})

		return action == 'download_rm' and bom_dict or pp_items
