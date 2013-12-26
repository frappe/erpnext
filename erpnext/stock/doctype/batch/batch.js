// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

cur_frm.fields_dict['item'].get_query = function(doc, cdt, cdn) {
	return {
		query: "erpnext.controllers.queries.item_query",
		filters:{
			'is_stock_item': 'Yes'	
		}
	}	
}