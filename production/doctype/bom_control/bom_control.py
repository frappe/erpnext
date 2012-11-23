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

# Please edit this list and import only required elements
from __future__ import unicode_literals
import webnotes

from webnotes.utils import cint, flt
from webnotes.model import db_exists
from webnotes.model.doc import Document, addchild, getchildren, make_autoname
from webnotes.model.wrapper import getlist, copy_doclist
from webnotes.model.code import get_obj, get_server_obj, run_server_obj, updatedb, check_syntax
from webnotes import session, form, msgprint, errprint

set = webnotes.conn.set
sql = webnotes.conn.sql
get_value = webnotes.conn.get_value
in_transaction = webnotes.conn.in_transaction
convert_to_lists = webnotes.conn.convert_to_lists

# -----------------------------------------------------------------------------------------

	
class DocType:
	def __init__(self, doc, doclist):
		self.doc = doc
		self.doclist = doclist



	def get_item_group(self):
		ret = sql("select name from `tabItem Group` ")
		item_group = []
		for r in ret:
			item =sql("select t1.name from `tabItem` t1, `tabBOM` t2 where t2.item = t1.name and t1.item_group = '%s' " % (r[0]))
			if item and item[0][0]:
				item_group.append(r[0])
		return '~~~'.join([r for r in item_group])



	def get_item_code(self,item_group):
		""" here BOM docstatus = 1 and is_active ='yes' condition is not given because some bom
			is under construction that is it is still in saved mode and they want see till where they have reach.
		"""
		ret = sql("select distinct t1.name from `tabItem` t1, `tabBOM` t2 where t2.item = t1.name and t1.item_group = '%s' " % (item_group))
		return '~~~'.join([r[0] for r in ret])



	def get_bom_no(self,item_code):
		ret = sql("select name from `tabBOM` where item = '%s' " % (item_code))
		return '~~~'.join([r[0] for r in ret])



	def get_operations(self,bom_no):
		ret = sql("select operation_no,opn_description,workstation,hour_rate,time_in_mins from `tabBOM Operation` where parent = %s", bom_no, as_dict = 1)
		cost = sql("select dir_mat_as_per_mar , operating_cost , cost_as_per_mar from `tabBOM` where name = %s", bom_no, as_dict = 1)

		# Validate the BOM ENTRIES
		reply = []

		if ret:
			for r in ret:
				reply.append(['operation',cint(r['operation_no']), r['opn_description'] or '','%s'% bom_no,r['workstation'],flt(r['hour_rate']),flt(r['time_in_mins']),0,0,0])

			reply[0][7]= flt(cost[0]['dir_mat_as_per_mar'])
			reply[0][8]=flt(cost[0]['operating_cost'])
			reply[0][9]=flt(cost[0]['cost_as_per_mar'])
		return reply



	def get_item_bom(self,data):
		data = eval(data)
		reply = []
		ret = sql("select item_code,description,bom_no,qty,scrap,stock_uom,value_as_per_mar,moving_avg_rate from `tabBOM Item` where parent = '%s' and operation_no = '%s'" % (data['bom_no'],data['op_no']), as_dict =1 )

		for r in ret:
			item = sql("select is_manufactured_item, is_sub_contracted_item from `tabItem` where name = '%s'" % r['item_code'], as_dict=1)
			if not item[0]['is_manufactured_item'] == 'Yes' and not item[0]['is_sub_contracted_item'] =='Yes':
				#if item is not manufactured or it is not sub-contracted
				reply.append([ 'item_bom', r['item_code'] or '', r['description'] or '', r['bom_no'] or '', flt(r['qty']) or 0, r['stock_uom'] or '', flt(r['scrap']) or 0, flt(r['moving_avg_rate']) or 0, 1])
			else:
				# if it is manufactured or sub_contracted this will be considered(here item can be purchase item)
				reply.append([ 'item_bom', r['item_code'] or '', r['description'] or '', r['bom_no'] or '', flt(r['qty']) or 0, r['stock_uom'] or '', flt(r['scrap']) or 0, flt(r['value_as_per_mar']) or 0, 0])
		return reply



	#------------- Wrapper Code --------------
	def calculate_cost(self, bom_no):
		main_bom_list = get_obj('Production Control').traverse_bom_tree( bom_no = bom_no, qty = 1, calculate_cost = 1)
		main_bom_list.reverse()
		for bom in main_bom_list:
			bom_obj = get_obj('BOM', bom, with_children = 1)
			bom_obj.calculate_cost()
		return 'calculated'



	def get_bom_tree_list(self,args):
		arg = eval(args)
		i =[]
		for a in sql("select t1.name from `tabBOM` t1, `tabItem` t2 where t2.item_group like '%s' and t1.item like '%s'"%(arg['item_group'] +'%',arg['item_code'] + '%')):
			if a[0] not in i:
				i.append(a[0])
		return i
