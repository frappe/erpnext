// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
frappe.ui.form.on('Production', {
	setup:function(frm){
		if (frm.doc.__islocal){
			frm.set_value("posting_time",frappe.datetime.now_time())
			frm.refresh_field("posting_time")
		}
	},
    refresh:function(frm){
		if(frm.doc.docstatus == 1) {
			cur_frm.add_custom_button(__("Stock Ledger"), function() {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.posting_date,
					to_date: frm.doc.posting_date,
					company: frm.doc.company
				};
				frappe.set_route("query-report", "Stock Ledger");
			}, __("View"));

			cur_frm.add_custom_button(__('Accounting Ledger'), function() {
				frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.posting_date,
					to_date: frm.doc.posting_date,
					company: frm.doc.company,
					group_by_voucher: false
				};
				frappe.set_route("query-report", "General Ledger");
			}, __("View"));
		}
	},
    branch:function(frm){
        cur_frm.set_query("warehouse", function() {
            return {
                query: "erpnext.controllers.queries.filter_branch_wh",
                filters: {'branch': frm.doc.branch}
            }
        });
        cur_frm.set_query("cop_list", function() {
            return {
                query: "erpnext.controllers.queries.filter_cop",
                filters: {'branch': frm.doc.branch}
            }
        });
    },
	warehouse:function(frm){
		assign_warehouse_and_cost_center(frm)
	},
	cost_center:function(frm){
		assign_warehouse_and_cost_center(frm)
	},
	production_based_on:function(frm){
		if(frm.doc.production_based_on){
			console.log(frm.doc.production_based_on)
			cur_frm.set_query("production_settings",function(){
				return{
					filters:{based_on:frm.doc.production_based_on}
				}
			})
		}
	},
	get_raw_material:function(frm){
		get_raw_materials(frm)
	},
	get_product:function(frm){
		get_finish_product(frm)
	}
});

frappe.ui.form.on("Production Product Item", {
	items_add: function(frm, cdt, cdn){
		frappe.model.set_value(cdt, cdn, "warehouse", frm.doc.warehouse);
		frappe.model.set_value(cdt, cdn, "cost_center", frm.doc.cost_center);
	},
    item_code:function(frm,cdt,cdn){
		update_expense_account(frm, cdt, cdn);
        get_cop_rate(frm,cdt,cdn)
		check_item_applicable_for_coal_raising(frm,cdt,cdn)
    }
})
frappe.ui.form.on("Production Material Item", {
	item_code: function(frm, cdt, cdn){
		update_expense_account(frm, cdt, cdn);
	},
    items_add: function(frm, cdt, cdn){
		frappe.model.set_value(cdt, cdn, "warehouse", frm.doc.warehouse);
		frappe.model.set_value(cdt, cdn, "cost_center", frm.doc.cost_center);
	},
})
var assign_warehouse_and_cost_center= function(frm){
	if (frm.doc.raw_materials ){
		frm.doc.raw_materials.map(v=>{
			v.warehouse=frm.doc.warehouse
			v.cost_center = frm.doc.cost_center
		})
		frm.refresh_field("raw_materials")
	}
	if (frm.doc.items){
		frm.doc.items.map(v=>{
			v.warehouse=frm.doc.warehouse
			v.cost_center = frm.doc.cost_center
		})
		frm.refresh_field("items")
	}
}
var get_cop_rate = function(frm, cdt, cdn){
	let row = locals[cdt][cdn]
    if(row.item_code && frm.doc.cop_list){
		frappe.call({
			method: "erpnext.production.doctype.cop_rate.cop_rate.get_cop_rate",
			args: {
				"item_code": row.item_code,
				"posting_date":frm.doc.posting_date,
                "cop_list":frm.doc.cop_list,
                "uom":row.uom
			},
			callback: function(r){
				if (r.message.length > 0){
					frappe.model.set_value(cdt, cdn, "cop", r.message[0].rate);
					cur_frm.refresh_field("items");
				}
			}
		})
	}else{
		frappe.throw("COP List or Item is missing to fetch COP")
	}
}
cur_frm.fields_dict['raw_materials'].grid.get_field('item_code').get_query = function(frm, cdt, cdn) {
	return {
        filters: {
            "disabled": 0,
            "is_production_item": 1,
        }
    };
}

cur_frm.fields_dict['items'].grid.get_field('item_code').get_query = function(frm, cdt, cdn) {
	return {
        filters: {
            "disabled": 0,
            "is_production_item": 1,
        }
    };
}
cur_frm.fields_dict['items'].grid.get_field('equipment').get_query = function(frm, cdt, cdn) {
	return {
        filters: {
            "enabled": 1
		    }
    };
}
var update_expense_account = function(frm, cdt, cdn){
	let row = locals[cdt][cdn];
	if(row.item_code){
		frappe.call({
			method: "erpnext.production.doctype.production.production.get_expense_account",
			args: {
				"company": frm.doc.company,
				"item": row.item_code,
			},
			callback: function(r){
				console.log(r.message)
				frappe.model.set_value(cdt, cdn, "expense_account", r.message);
				cur_frm.refresh_field(cdt, cdn, "expense_account");
			}
		})
	}
}
function get_finish_product(frm){
	if (frm.doc.branch && frm.doc.raw_materials){
		return frappe.call({
				method: "get_finish_product",
				doc: cur_frm.doc,
				callback: function(r, rt){					
					if(r.message){
						console.log(r.message);
						cur_frm.clear_table("items");
						cur_frm.clear_table("production_waste");
						r.message.forEach(function(rec) {
							if(rec['parameter_type'] == "Item")
							{	
								var row = frappe.model.add_child(cur_frm.doc, "Production Product Item", "items");
								row.item_code = rec['item_code'];
								row.item_name = rec['item_name'];
								row.item_type = rec['item_type'];		
								row.qty = rec['qty'];
								row.uom = rec['uom'];
								row.item_group = rec['item_group'];
								row.price_template = rec['price_template'];
								row.cop = rec['cop'];
								row.cost_center = rec['cost_center'];
								row.warehouse = rec['warehouse'];
								row.expense_account = rec['expense_account'];
								row.ratio = rec['ratio'];
							}
							else{
								var row = frappe.model.add_child(cur_frm.doc, "Production Waste", "production_waste");
								row.parameter_code = rec['item_code'];
								row.item_name = rec['item_name'];
								row.ratio = rec['ratio'];		
								row.qty = rec['qty'];
								row.uom = rec['uom'];
							}
						});
					}
					else
					{
						cur_frm.clear_table("items");
					}					
				cur_frm.refresh();
				},
            });     
	}else{
		frappe.msgprint("To get the finish product, please enter the branch and raw material");
	}
}
var check_item_applicable_for_coal_raising =(frm,cdt,cdn)=>{
	var row = locals[cdt][cdn];
	frappe.call({
		method:'check_item_applicable_for_coal_raising',
		args:{
			'item':row.item_code
		},
		callback:function(r){
			if(r.message){
				frm.set_df_property('coal_raising_type', 'reqd', 1)
			}else{
				frm.set_df_property('coal_raising_type', 'reqd', 0)
			}
		}
	})
}
function get_raw_materials(frm){
	if (frm.doc.branch && frm.doc.items){
		return frappe.call({
				method: "get_raw_material",
				doc: cur_frm.doc,
				callback: function(r, rt){					
					if(r.message){
						console.log(r.message);
						cur_frm.clear_table("raw_materials");
						r.message.forEach(function(rec) {
							if(rec['parameter_type'] == "Item")
							{	
								var row = frappe.model.add_child(cur_frm.doc, "Production Material Item", "raw_materials");
								row.item_code = rec['item_code'];
								row.item_name = rec['item_name'];	
								row.item_type = rec['item_type'];	
								row.qty = rec['qty'];
								row.uom = rec['uom'];
								row.cost_center = rec['cost_center'];
								row.warehouse = rec['warehouse'];
								row.expense_account = rec['expense_account'];
							}
						});
					}
					else
					{
						cur_frm.clear_table("raw_materials");
					}					
				cur_frm.refresh();
				},
            });     
	}else{
		frappe.msgprint("To get the Raw Materials, please enter the branch and finish product in Production Setting");
	}
}

var check_item_applicable_for_coal_raising =(frm,cdt,cdn)=>{
	var row = locals[cdt][cdn];
	frappe.call({
		method:'erpnext.production.doctype.production.production.check_item_applicable_for_coal_raising',
		args:{
			'item':row.item_code
		},
		callback:function(r){
			if(r.message){
				frm.set_df_property('coal_raising_type', 'reqd', 1)
			}else{
				frm.set_df_property('coal_raising_type', 'reqd', 0)
			}
		}
	})
}