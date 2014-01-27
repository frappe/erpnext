# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import cstr, flt, cint, nowdate, add_days
from webnotes.model.doc import addchild, Document
from webnotes.model.bean import getlist
from webnotes.model.code import get_obj
from webnotes import msgprint, _

class DocType:
	def __init__(self, doc, doclist=[]):
		self.doc = doc
		self.doclist = doclist
		self.item_dict = {}

	def get_so_details(self, so):
		"""Pull other details from so"""
		so = webnotes.conn.sql("""select transaction_date, customer, grand_total 
			from `tabSales Order` where name = %s""", so, as_dict = 1)
		ret = {
			'sales_order_date': so and so[0]['transaction_date'] or '',
			'customer' : so[0]['customer'] or '',
			'grand_total': so[0]['grand_total']
		}
		return ret	
			
	def get_item_details(self, item_code):
		""" Pull other item details from item master"""

		item = webnotes.conn.sql("""select description, stock_uom, default_bom 
			from `tabItem` where name = %s""", item_code, as_dict =1)
		ret = {
			'description'	: item and item[0]['description'],
			'stock_uom'		: item and item[0]['stock_uom'],
			'bom_no'		: item and item[0]['default_bom']
		}
		return ret

	def clear_so_table(self):
		self.doclist = self.doc.clear_table(self.doclist, 'pp_so_details')

	def clear_item_table(self):
		self.doclist = self.doc.clear_table(self.doclist, 'pp_details')
		
	def validate_company(self):
		if not self.doc.company:
			webnotes.throw(_("Please enter Company"))

	def get_open_sales_orders(self):
		""" Pull sales orders  which are pending to deliver based on criteria selected"""
		so_filter = item_filter = ""
		if self.doc.from_date:
			so_filter += ' and so.transaction_date >= "' + self.doc.from_date + '"'
		if self.doc.to_date:
			so_filter += ' and so.transaction_date <= "' + self.doc.to_date + '"'
		if self.doc.customer:
			so_filter += ' and so.customer = "' + self.doc.customer + '"'
			
		if self.doc.fg_item:
			item_filter += ' and item.name = "' + self.doc.fg_item + '"'
		
		open_so = webnotes.conn.sql("""
			select distinct so.name, so.transaction_date, so.customer, so.grand_total
			from `tabSales Order` so, `tabSales Order Item` so_item
			where so_item.parent = so.name
				and so.docstatus = 1 and so.status != "Stopped"
				and so.company = %s
				and ifnull(so_item.qty, 0) > ifnull(so_item.delivered_qty, 0) %s
				and (exists (select name from `tabItem` item where item.name=so_item.item_code
					and (ifnull(item.is_pro_applicable, 'No') = 'Yes' 
						or ifnull(item.is_sub_contracted_item, 'No') = 'Yes') %s)
					or exists (select name from `tabPacked Item` pi
						where pi.parent = so.name and pi.parent_item = so_item.item_code
							and exists (select name from `tabItem` item where item.name=pi.item_code
								and (ifnull(item.is_pro_applicable, 'No') = 'Yes' 
									or ifnull(item.is_sub_contracted_item, 'No') = 'Yes') %s)))
			""" % ('%s', so_filter, item_filter, item_filter), self.doc.company, as_dict=1)
		
		self.add_so_in_table(open_so)

	def add_so_in_table(self, open_so):
		""" Add sales orders in the table"""
		self.clear_so_table()

		so_list = [d.sales_order for d in getlist(self.doclist, 'pp_so_details')]
		for r in open_so:
			if cstr(r['name']) not in so_list:
				pp_so = addchild(self.doc, 'pp_so_details', 
					'Production Plan Sales Order', self.doclist)
				pp_so.sales_order = r['name']
				pp_so.sales_order_date = cstr(r['transaction_date'])
				pp_so.customer = cstr(r['customer'])
				pp_so.grand_total = flt(r['grand_total'])

	def get_items_from_so(self):
		""" Pull items from Sales Order, only proction item
			and subcontracted item will be pulled from Packing item 
			and add items in the table
		"""
		items = self.get_items()
		self.add_items(items)

	def get_items(self):
		so_list = filter(None, [d.sales_order for d in getlist(self.doclist, 'pp_so_details')])
		if not so_list:
			msgprint(_("Please enter sales order in the above table"))
			return []
			
		items = webnotes.conn.sql("""select distinct parent, item_code, reserved_warehouse,
			(qty - ifnull(delivered_qty, 0)) as pending_qty
			from `tabSales Order Item` so_item
			where parent in (%s) and docstatus = 1 and ifnull(qty, 0) > ifnull(delivered_qty, 0)
			and exists (select * from `tabItem` item where item.name=so_item.item_code
				and (ifnull(item.is_pro_applicable, 'No') = 'Yes' 
					or ifnull(item.is_sub_contracted_item, 'No') = 'Yes'))""" % \
			(", ".join(["%s"] * len(so_list))), tuple(so_list), as_dict=1)
		
		packed_items = webnotes.conn.sql("""select distinct pi.parent, pi.item_code, pi.warehouse as reserved_warhouse,
			(((so_item.qty - ifnull(so_item.delivered_qty, 0)) * pi.qty) / so_item.qty) 
				as pending_qty
			from `tabSales Order Item` so_item, `tabPacked Item` pi
			where so_item.parent = pi.parent and so_item.docstatus = 1 
			and pi.parent_item = so_item.item_code
			and so_item.parent in (%s) and ifnull(so_item.qty, 0) > ifnull(so_item.delivered_qty, 0)
			and exists (select * from `tabItem` item where item.name=pi.item_code
				and (ifnull(item.is_pro_applicable, 'No') = 'Yes' 
					or ifnull(item.is_sub_contracted_item, 'No') = 'Yes'))""" % \
			(", ".join(["%s"] * len(so_list))), tuple(so_list), as_dict=1)

		return items + packed_items
		

	def add_items(self, items):
		self.clear_item_table()

		for p in items:
			item_details = webnotes.conn.sql("""select description, stock_uom, default_bom 
				from tabItem where name=%s""", p['item_code'])
			pi = addchild(self.doc, 'pp_details', 'Production Plan Item', self.doclist)
			pi.sales_order				= p['parent']
			pi.warehouse				= p['reserved_warehouse']
			pi.item_code				= p['item_code']
			pi.description				= item_details and item_details[0][0] or ''
			pi.stock_uom				= item_details and item_details[0][1] or ''
			pi.bom_no					= item_details and item_details[0][2] or ''
			pi.so_pending_qty			= flt(p['pending_qty'])
			pi.planned_qty				= flt(p['pending_qty'])
	

	def validate_data(self):
		self.validate_company()
		for d in getlist(self.doclist, 'pp_details'):
			self.validate_bom_no(d)
			if not flt(d.planned_qty):
				webnotes.throw("Please Enter Planned Qty for item: %s at row no: %s" % 
					(d.item_code, d.idx))
				
	def validate_bom_no(self, d):
		if not d.bom_no:
			webnotes.throw("Please enter bom no for item: %s at row no: %s" % 
				(d.item_code, d.idx))
		else:
			bom = webnotes.conn.sql("""select name from `tabBOM` where name = %s and item = %s 
				and docstatus = 1 and is_active = 1""", 
				(d.bom_no, d.item_code), as_dict = 1)
			if not bom:
				webnotes.throw("""Incorrect BOM No: %s entered for item: %s at row no: %s
					May be BOM is inactive or for other item or does not exists in the system""" % 
					(d.bom_no, d.item_doce, d.idx))

	def raise_production_order(self):
		"""It will raise production order (Draft) for all distinct FG items"""
		self.validate_data()

		from utilities.transaction_base import validate_uom_is_integer
		validate_uom_is_integer(self.doclist, "stock_uom", "planned_qty")

		items = self.get_distinct_items_and_boms()[1]
		pro = self.create_production_order(items)
		if pro:
			pro = ["""<a href="#Form/Production Order/%s" target="_blank">%s</a>""" % \
				(p, p) for p in pro]
			msgprint(_("Production Order(s) created:\n\n") + '\n'.join(pro))
		else :
			msgprint(_("No Production Order created."))

	def get_distinct_items_and_boms(self):
		""" Club similar BOM and item for processing
			bom_dict {
				bom_no: ['sales_order', 'qty']
			}
		"""
		item_dict, bom_dict = {}, {}
		for d in self.doclist.get({"parentfield": "pp_details"}):			
			bom_dict.setdefault(d.bom_no, []).append([d.sales_order, flt(d.planned_qty)])
			item_dict[(d.item_code, d.sales_order, d.warehouse)] = {
				"production_item"	: d.item_code,
				"sales_order"		: d.sales_order,
				"qty" 				: flt(item_dict.get((d.item_code, d.sales_order, d.warehouse),
										{}).get("qty")) + flt(d.planned_qty),
				"bom_no"			: d.bom_no,
				"description"		: d.description,
				"stock_uom"			: d.stock_uom,
				"company"			: self.doc.company,
				"wip_warehouse"		: "",
				"fg_warehouse"		: d.warehouse,
				"status"			: "Draft",
			}
		return bom_dict, item_dict
		
	def create_production_order(self, items):
		"""Create production order. Called from Production Planning Tool"""
		from manufacturing.doctype.production_order.production_order import OverProductionError

		pro_list = []
		for key in items:
			pro = webnotes.new_bean("Production Order")
			pro.doc.fields.update(items[key])
			
			webnotes.flags.mute_messages = True
			try:
				pro.insert()
				pro_list.append(pro.doc.name)
			except OverProductionError, e:
				pass
				
			webnotes.flags.mute_messages = False
			
		return pro_list

	def download_raw_materials(self):
		""" Create csv data for required raw material to produce finished goods"""
		self.validate_data()
		bom_dict = self.get_distinct_items_and_boms()[0]
		self.get_raw_materials(bom_dict)
		return self.get_csv()

	def get_raw_materials(self, bom_dict):
		""" Get raw materials considering sub-assembly items 
			{
				"item_code": [qty_required, description, stock_uom, min_order_qty]
			}
		"""
		item_list = []

		for bom, so_wise_qty in bom_dict.items():
			bom_wise_item_details = {}
			if self.doc.use_multi_level_bom:
				# get all raw materials with sub assembly childs					
				for d in webnotes.conn.sql("""select fb.item_code, 
					ifnull(sum(fb.qty_consumed_per_unit), 0) as qty, 
					fb.description, fb.stock_uom, it.min_order_qty 
					from `tabBOM Explosion Item` fb,`tabItem` it 
					where it.name = fb.item_code and ifnull(it.is_pro_applicable, 'No') = 'No' 
					and ifnull(it.is_sub_contracted_item, 'No') = 'No' 
					and fb.docstatus<2 and fb.parent=%s 
					group by item_code, stock_uom""", bom, as_dict=1):
						bom_wise_item_details.setdefault(d.item_code, d)
			else:
				# Get all raw materials considering SA items as raw materials, 
				# so no childs of SA items
				for d in webnotes.conn.sql("""select bom_item.item_code, 
					ifnull(sum(bom_item.qty_consumed_per_unit), 0) as qty, 
					bom_item.description, bom_item.stock_uom, item.min_order_qty 
					from `tabBOM Item` bom_item, tabItem item 
					where bom_item.parent = %s and bom_item.docstatus < 2 
					and bom_item.item_code = item.name 
					group by item_code""", bom, as_dict=1):
						bom_wise_item_details.setdefault(d.item_code, d)

			for item, item_details in bom_wise_item_details.items():
				for so_qty in so_wise_qty:
					item_list.append([item, flt(item_details.qty) * so_qty[1], item_details.description, 
						item_details.stock_uom, item_details.min_order_qty, so_qty[0]])

			self.make_items_dict(item_list)

	def make_items_dict(self, item_list):
		for i in item_list:
			self.item_dict.setdefault(i[0], []).append([flt(i[1]), i[2], i[3], i[4], i[5]])

	def get_csv(self):
		item_list = [['Item Code', 'Description', 'Stock UOM', 'Required Qty', 'Warehouse',
		 	'Quantity Requested for Purchase', 'Ordered Qty', 'Actual Qty']]
		for item in self.item_dict:
			total_qty = sum([flt(d[0]) for d in self.item_dict[item]])
			for item_details in self.item_dict[item]:
				item_list.append([item, item_details[1], item_details[2], item_details[0]])
				item_qty = webnotes.conn.sql("""select warehouse, indented_qty, ordered_qty, actual_qty 
					from `tabBin` where item_code = %s""", item, as_dict=1)
				i_qty, o_qty, a_qty = 0, 0, 0
				for w in item_qty:
					i_qty, o_qty, a_qty = i_qty + flt(w.indented_qty), o_qty + flt(w.ordered_qty), a_qty + flt(w.actual_qty)
					item_list.append(['', '', '', '', w.warehouse, flt(w.indented_qty), 
						flt(w.ordered_qty), flt(w.actual_qty)])
				if item_qty:
					item_list.append(['', '', '', '', 'Total', i_qty, o_qty, a_qty])

		return item_list
		
	def raise_purchase_request(self):
		"""
			Raise Material Request if projected qty is less than qty required
			Requested qty should be shortage qty considering minimum order qty
		"""
		self.validate_data()
		if not self.doc.purchase_request_for_warehouse:
			webnotes.throw(_("Please enter Warehouse for which Material Request will be raised"))
			
		bom_dict = self.get_distinct_items_and_boms()[0]		
		self.get_raw_materials(bom_dict)
		
		if self.item_dict:
			self.insert_purchase_request()

	def get_requested_items(self):
		item_projected_qty = self.get_projected_qty()
		items_to_be_requested = webnotes._dict()

		for item, so_item_qty in self.item_dict.items():
			requested_qty = 0
			total_qty = sum([flt(d[0]) for d in so_item_qty])
			if total_qty > item_projected_qty.get(item, 0):
				# shortage
				requested_qty = total_qty - item_projected_qty.get(item, 0)
				# consider minimum order qty
				requested_qty = requested_qty > flt(so_item_qty[0][3]) and \
					requested_qty or flt(so_item_qty[0][3])

			# distribute requested qty SO wise
			for item_details in so_item_qty:
				if requested_qty:
					sales_order = item_details[4] or "No Sales Order"
					if requested_qty <= item_details[0]:
						adjusted_qty = requested_qty
					else:
						adjusted_qty = item_details[0]

					items_to_be_requested.setdefault(item, {}).setdefault(sales_order, 0)
					items_to_be_requested[item][sales_order] += adjusted_qty
					requested_qty -= adjusted_qty
				else:
					break

			# requested qty >= total so qty, due to minimum order qty
			if requested_qty:
				items_to_be_requested.setdefault(item, {}).setdefault("No Sales Order", 0)
				items_to_be_requested[item]["No Sales Order"] += requested_qty

		return items_to_be_requested
			
	def get_projected_qty(self):
		items = self.item_dict.keys()
		item_projected_qty = webnotes.conn.sql("""select item_code, sum(projected_qty) 
			from `tabBin` where item_code in (%s) group by item_code""" % 
			(", ".join(["%s"]*len(items)),), tuple(items))

		return dict(item_projected_qty)
		
	def insert_purchase_request(self):
		items_to_be_requested = self.get_requested_items()

		from accounts.utils import get_fiscal_year
		fiscal_year = get_fiscal_year(nowdate())[0]

		purchase_request_list = []
		if items_to_be_requested:
			for item in items_to_be_requested:
				item_wrapper = webnotes.bean("Item", item)
				pr_doclist = [{
					"doctype": "Material Request",
					"__islocal": 1,
					"naming_series": "IDT",
					"transaction_date": nowdate(),
					"status": "Draft",
					"company": self.doc.company,
					"fiscal_year": fiscal_year,
					"requested_by": webnotes.session.user,
					"material_request_type": "Purchase"
				}]
				for sales_order, requested_qty in items_to_be_requested[item].items():
					pr_doclist.append({
						"doctype": "Material Request Item",
						"__islocal": 1,
						"parentfield": "indent_details",
						"item_code": item,
						"item_name": item_wrapper.doc.item_name,
						"description": item_wrapper.doc.description,
						"uom": item_wrapper.doc.stock_uom,
						"item_group": item_wrapper.doc.item_group,
						"brand": item_wrapper.doc.brand,
						"qty": requested_qty,
						"schedule_date": add_days(nowdate(), cint(item_wrapper.doc.lead_time_days)),
						"warehouse": self.doc.purchase_request_for_warehouse,
						"sales_order_no": sales_order if sales_order!="No Sales Order" else None
					})

				pr_wrapper = webnotes.bean(pr_doclist)
				pr_wrapper.ignore_permissions = 1
				pr_wrapper.submit()
				purchase_request_list.append(pr_wrapper.doc.name)
			
			if purchase_request_list:
				pur_req = ["""<a href="#Form/Material Request/%s" target="_blank">%s</a>""" % \
					(p, p) for p in purchase_request_list]
				msgprint("Material Request(s) created: \n%s" % 
					"\n".join(pur_req))
		else:
			msgprint(_("Nothing to request"))