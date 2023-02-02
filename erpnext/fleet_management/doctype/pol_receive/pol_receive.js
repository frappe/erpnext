// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('POL Receive', {
	refresh: function(frm) {
		if (frm.doc.docstatus === 1 && frm.doc.use_common_fuelbook == 1) {
			frm.add_custom_button(
				__("Ledger"),
				function () {
				  frappe.route_options = {
					voucher_no: frm.doc.name,
					from_date: frm.doc.entry_date,
					to_date: frm.doc.entry_date,
					company: frm.doc.company,
					group_by_voucher: false,
				  };
				  frappe.set_route("query-report", "General Ledger");
				},
				__("View")
			  );
		}
	},
	qty: function(frm) {
		calculate_total(frm)
		frm.events.reset_items()
		frm.refresh_fields("items")
	},
	direct_consumption:function(frm){
		set_equipment_filter(frm)
	},
	rate: function(frm) {
		frm.events.reset_items()
		frm.refresh_fields("items")
		calculate_total(frm)
	},
	get_pol_expense:function(frm){
		populate_child_table(frm)
	},
	branch:function(frm){
		frm.set_query("equipment",function(){
			return {
				filters:{
					"branch":frm.doc.branch,
					"enabled":1
				}
			}
		})
	},
	equipment:function(frm){
		frm.set_query("fuelbook",function(){
			return {
				filters:{
					"equipment":frm.doc.equipment
				}
			}
		})
	},
	use_common_fuelbook:function(frm){
		frm.set_query("fuelbook",function(){
			return {
				filters:{
					"type":"Common",
					"branch":frm.doc.branch
				}
			}
		})
		if(frm.doc.use_common_fuelbook){
			frm.set_query("equipment",function(){
				return {
					filters:{
						"branch":frm.doc.branch,
						"enabled":1,
						"hired_equipment":1
					}
				}
			})
		}
		else{
			frm.set_query("equipment",function(){
				return {
					filters:{
						"branch":frm.doc.branch,
						"enabled":1
					}
				}
			})
		}
	},
	reset_items:function(frm){
		cur_frm.clear_table("items");
	},
});
cur_frm.set_query("pol_type", function() {
	return {
		"filters": {
		"disabled": 0,
		"is_pol_item":1
		}
	};
});
var populate_child_table=(frm)=>{
	if (frm.doc.fuelbook && frm.doc.total_amount) {
		frappe.call({
			method: 'populate_child_table',
			doc: frm.doc,
			callback:  () =>{
				cur_frm.refresh_fields()
				frm.dirty()
			}
		})
	}
}
function calculate_total(frm) {
	if(frm.doc.qty && frm.doc.rate) {
		frm.set_value("total_amount", frm.doc.qty * frm.doc.rate)
	}

	if(frm.doc.qty && frm.doc.rate && frm.doc.discount_amount) {
		frm.set_value("total_amount", (frm.doc.qty * frm.doc.rate) - frm.doc.discount_amount)
	}
}	

var set_equipment_filter=function(frm){
	if ( cint(frm.doc.direct_consumption) == 0){
		frm.set_query("equipment", function() {
			return {
				query: "erpnext.fleet_management.fleet_utils.get_container_filtered",
				filters:{
					"branch":frm.doc.branch
				}
			};
		});
	}
}