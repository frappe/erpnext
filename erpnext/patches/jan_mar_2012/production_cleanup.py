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
def execute():
	import webnotes
	from webnotes.modules import reload_doc
	from webnotes.model import delete_doc
	sql = webnotes.conn.sql
	
	# Production Planning Tool
	#---------------------------------------------------------------
	#delete_doc('DocType', 'Production Plan Item')
	#delete_doc('DocType', 'Production Plan Sales Order')
	#delete_doc('DocType', 'Production Planning Tool')
	sql("delete from `tabDocField` where parent in ('Production Planning Tool', 'Production Plan Item', 'Production Plan Sales Order')")
	
	reload_doc('production', 'doctype', 'production_planning_tool')
	reload_doc('production', 'doctype', 'pp_detail')
	reload_doc('production', 'doctype', 'pp_so_detail')

	# Production Order
	#---------------------------------------------------------------

	reload_doc('production', 'doctype', 'production_order')

	sql("""delete from `tabDocField` where parent = 'Production Order'
			and (label in ('Material Transfer', 'Backflush', 'Stop Production Order', 'Unstop Production Order')
				or fieldname = 'transaction_date')
	""")


	# BOM
	#---------------------------------------------------------------
	reload_doc('production', 'doctype', 'bill_of_materials')
	reload_doc('production', 'doctype', 'bom_material')
	reload_doc('production', 'doctype', 'bom_operation')
	reload_doc('production', 'doctype', 'flat_bom_detail')

	#copy values
	sql("""update `tabBOM` set rm_cost_as_per = 'Valuation Rate', 
		raw_material_cost = dir_mat_as_per_mar,	total_cost = cost_as_per_mar, costing_date = cost_as_on""")

	sql("update `tabBOM Item` set rate = moving_avg_rate, amount = amount_as_per_mar")

	sql("update `tabBOM Explosion Item` set rate = moving_avg_rate, amount = amount_as_per_mar")



	# delete depricated flds from bom
	sql("""	delete from `tabDocField` where parent = 'BOM' 
		and (
			label in ('TreeView1', 'Set as Default BOM', 'Activate BOM', 'Inactivate BOM') 
			or fieldname in ('cost_as_per_mar', 'cost_as_per_lpr', 'cost_as_per_sr', 'cost_as_on',
				'dir_mat_as_per_mar', 'dir_mat_as_per_lpr', 'dir_mat_as_per_sr')
		)	
	""")

	# delete depricated flds from bom operation
	sql("delete from `tabDocField` where parent = 'BOM Operation' and fieldname in ('details', 'workstation_capacity')")

	# delete depricated flds from bom material
	sql("""delete from `tabDocField` where parent = 'BOM Item' 
		and fieldname in ('dir_mat_as_per_mar', 'dir_mat_as_per_sr', 'dir_mat_as_per_lpr', 'operating_cost', 'value_as_per_mar', 
			'value_as_per_sr', 'value_as_per_lpr', 'moving_avg_rate', 'standard_rate', 'last_purchase_rate', 'amount_as_per_sr', 
			'amount_as_per_lpr', 'amount_as_per_mar')	
	""")

	# delete depricated flds from flat bom
	sql("""delete from tabDocField where parent = 'BOM Explosion Item' 
		and fieldname in ('moving_avg_rate', 'standard_rate', 'last_purchase_rate', 'amount_as_per_mar', 
			'amount_as_per_sr', 'amount_as_per_lpr', 'flat_bom_no', 'bom_mat_no', 'is_pro_applicable')
	""")
