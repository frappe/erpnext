def execute():
	import webnotes
	from webnotes.modules.module_manager import reload_doc
	from webnotes.model import delete_doc
	sql = webnotes.conn.sql
	
	# Production Planning Tool
	#---------------------------------------------------------------
	#delete_doc('DocType', 'PP Detail')
	#delete_doc('DocType', 'PP SO Detail')
	#delete_doc('DocType', 'Production Planning Tool')
	sql("delete from `tabDocField` where parent in ('Production Planning Tool', 'PP Detail', 'PP SO Detail')")
	
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


	# Bill Of Materials
	#---------------------------------------------------------------
	reload_doc('production', 'doctype', 'bill_of_materials')
	reload_doc('production', 'doctype', 'bom_material')
	reload_doc('production', 'doctype', 'bom_operation')
	reload_doc('production', 'doctype', 'flat_bom_detail')

	#copy values
	sql("""update `tabBill Of Materials` set rm_cost_as_per = 'Valuation Rate', 
		raw_material_cost = dir_mat_as_per_mar,	total_cost = cost_as_per_mar, costing_date = cost_as_on""")

	sql("update `tabBOM Material` set rate = moving_avg_rate, amount = amount_as_per_mar")

	sql("update `tabFlat BOM Detail` set rate = moving_avg_rate, amount = amount_as_per_mar")



	# delete depricated flds from bom
	sql("""	delete from `tabDocField` where parent = 'Bill Of Materials' 
		and (
			label in ('TreeView1', 'Set as Default BOM', 'Activate BOM', 'Inactivate BOM') 
			or fieldname in ('cost_as_per_mar', 'cost_as_per_lpr', 'cost_as_per_sr', 'cost_as_on',
				'dir_mat_as_per_mar', 'dir_mat_as_per_lpr', 'dir_mat_as_per_sr')
		)	
	""")

	# delete depricated flds from bom operation
	sql("delete from `tabDocField` where parent = 'BOM Operation' and fieldname in ('details', 'workstation_capacity')")

	# delete depricated flds from bom material
	sql("""delete from `tabDocField` where parent = 'BOM Material' 
		and fieldname in ('dir_mat_as_per_mar', 'dir_mat_as_per_sr', 'dir_mat_as_per_lpr', 'operating_cost', 'value_as_per_mar', 
			'value_as_per_sr', 'value_as_per_lpr', 'moving_avg_rate', 'standard_rate', 'last_purchase_rate', 'amount_as_per_sr', 
			'amount_as_per_lpr', 'amount_as_per_mar')	
	""")

	# delete depricated flds from flat bom
	sql("""delete from tabDocField where parent = 'Flat BOM Detail' 
		and fieldname in ('moving_avg_rate', 'standard_rate', 'last_purchase_rate', 'amount_as_per_mar', 
			'amount_as_per_sr', 'amount_as_per_lpr', 'flat_bom_no', 'bom_mat_no', 'is_pro_applicable')
	""")
