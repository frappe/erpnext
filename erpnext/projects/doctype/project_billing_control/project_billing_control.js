// Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Project Billing Control', {
	refresh: function(frm) {
		if(!frm.doc.__islocal) {
	       frm.add_custom_button(__('Issue Invoice Request'), function() { 
	        // click
	      });
	    }


	},
	project_name: function(frm) {
		cur_frm.set_value("scope_item", );
		cur_frm.set_value("items_value", '0');
		cur_frm.set_value("description", );
		cur_frm.set_value("billing_percentage", '0');
		cur_frm.set_value("billing_value", '0');
		cur_frm.set_value("total_project_billing_so_far", '0');
		cur_frm.set_value("total_scope_item_billing_so_far", '0');

		if(cur_frm.doc.project_name){
			frappe.call({
	            method: "get_project_payment_schedule",
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
				    	cur_frm.set_value("items_value", '0');
				    	cur_frm.set_value("billing_percentage", '0');
				    	cur_frm.set_value("total_scope_item_billing_so_far", '0');
				    	cur_frm.set_value("billing_value", '0');
				    	cur_frm.set_value("total_project_billing_so_far", '0');

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
	    	cur_frm.set_value("items_value", '0');
	    	cur_frm.set_value("billing_percentage", '0');
	    	cur_frm.set_value("total_scope_item_billing_so_far", '0');
	    	cur_frm.set_value("billing_value", '0');
	    	cur_frm.set_value("total_project_billing_so_far", '0');

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
		cur_frm.set_value("items_value", '0');
		cur_frm.set_value("description", );
		cur_frm.set_value("billing_percentage", '0');
		cur_frm.set_value("billing_value", '0');
		cur_frm.set_value("total_project_billing_so_far", '0');
		cur_frm.set_value("total_scope_item_billing_so_far", '0');

		if(cur_frm.doc.scope_item){
			frappe.call({
	            method: "get_item_cost",
	            doc: frm.doc,
	            callback: function(r) {
	            	// console.log(r.message)
	                if (r.message) {
	                    cur_frm.set_value("items_value", r.message[0]);
	                    cur_frm.set_value("billing_percentage", r.message[1]);
	                    cur_frm.set_value("billing_value", r.message[2]);
	                    if(r.message[4] != 0){
	                    	cur_frm.set_value("total_project_billing_so_far", r.message[3]);
	                    }else{
	                    	cur_frm.set_value("total_project_billing_so_far", '0');
		                }
	                	cur_frm.set_value("total_scope_item_billing_so_far", r.message[4]);
	                }else{
	                	cur_frm.set_value("items_value", '0');
	                	cur_frm.set_value("billing_percentage", '0');
	                	cur_frm.set_value("billing_value", '0');
	                	cur_frm.set_value("total_project_billing_so_far", '0');
	                	cur_frm.set_value("total_scope_item_billing_so_far", '0');
	                }
	            }
	        });
	    }

	}

	
});

