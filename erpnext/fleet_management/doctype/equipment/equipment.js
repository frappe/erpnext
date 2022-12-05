// Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Equipment', {
	setup:function(frm){
		frm.set_query("asset_code",function(doc){
			return {
				filters:{
					docstatus:1
				}
			}
		})
	},
	refresh: function(frm) {
		frm.add_custom_button(__('Maintain History'), function(doc) {
			frm.events.create_equipment_history(frm)
		},__("Create"))
	},
	equipment_category:function(frm){
		frm.set_query('equipment_type', function(doc) {
			return {
				filters: {
					"disabled": 0,
					"equipment_category": doc.equipment_category
				}
			};
		});
	},
	equipment_type:function(frm){
		frm.set_query('equipment_model', function(doc) {
			return {
				filters: {
					"disabled": 0,
				}
			};
		});
	},
	create_equipment_history:function(frm){
		frappe.call({
			method:"create_equipment_history",
			doc:frm.doc,
			args:{
				branch:frm.doc.branch,
				on_date:frappe.datetime.now_date(),
				ref_doc:frm.doc.name,
				purpose:"Submit"
			},
			callback:function(r){
				frm.refresh_field("equipment_history")
				frm.dirty()
			}
		})
	}
});
