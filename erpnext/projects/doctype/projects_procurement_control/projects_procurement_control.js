// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Projects Procurement Control', {
	refresh: function(frm) {
		if(!frm.doc.__islocal) {
	       frm.add_custom_button(__('Issue a P.R. Request'), function() { 
	        // click
	      });
	    }

	},
	project_name: function(frm) {
		cur_frm.set_value("scope_item", );
		cur_frm.set_value("description", );
		cur_frm.set_value("items_cost_price", '0');
		cur_frm.set_value("remaining_of_items_cost_price", '0');
		cur_frm.set_value("cost_value", '0');
		cur_frm.set_value("incurred_limit", );
		cur_frm.set_value("attach_relevant_quotation", );
		cur_frm.set_value("total_project_expense_so_far", '0');

		if(cur_frm.doc.project_name){
			frappe.call({
	            method: "get_project_item",
	            doc: frm.doc,
	            callback: function(r) {
	                if (r.message) {

	                    cur_frm.set_query("scope_item", function() {
			                return {
			                    filters: [
			                        ["Item", "name", "in", r.message],
			                    ]
			                };
			            });

	                }else{
	                	cur_frm.set_value("scope_item", );

	                	cur_frm.set_query("scope_item", function() {
			                return {
			                    filters: [
			                        ["Item", "name", "=", ''],
			                    ]
			                };
			            });
	                }
	            }
	        });
	    }else{
	    	cur_frm.set_value("scope_item", );

	    	cur_frm.set_query("scope_item", function() {
                return {
                    filters: [
                        ["Item", "name", "=", ''],
                    ]
                };
            });
	    }

	},
	scope_item: function(frm) {
		cur_frm.set_value("description", );
		cur_frm.set_value("items_cost_price", '0');
		cur_frm.set_value("remaining_of_items_cost_price", '0');
		cur_frm.set_value("cost_value", '0');
		cur_frm.set_value("incurred_limit", );
		cur_frm.set_value("attach_relevant_quotation", );
		cur_frm.set_value("total_project_expense_so_far", '0');

		if(cur_frm.doc.scope_item){
			frappe.call({
	            method: "get_item_cost",
	            doc: frm.doc,
	            callback: function(r) {
	            	// console.log(r.message)
	                if (r.message) {
	                    cur_frm.set_value("items_cost_price", r.message[0]);
	                    cur_frm.set_value("cost_value", r.message[1]);
	                    cur_frm.set_value("remaining_of_items_cost_price", r.message[0]-r.message[1] );

	                }else{
	                	cur_frm.set_value("items_cost_price", '0');
	                	cur_frm.set_value("cost_value", '0');
	                	cur_frm.set_value("cost_value", '0');

	                }
	            }
	        });
	    }

	}

});
