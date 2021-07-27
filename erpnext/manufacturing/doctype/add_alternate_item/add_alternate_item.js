// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Add Alternate Item', {
	add_additional_item: function(frm){
		frappe.call({
			method:'get_aditional_item_data',
			doc: frm.doc,
			callback: function(resp){
				if(resp.message){
					frm.refresh_fields('item')
					
					//var table = locals[cdt][cdn].item
					frm.set_query('alternate_item_code', 'item', () => {
						return {
							filters: {
								item_code: ['in',resp.message]
							}
						}
					})
					frm.refresh_fields('item')
				}
				
			}
		})
	},
	work_order: function(frm){
		frappe.call({
			method:'get_wo_item_data',
			doc: frm.doc,
			callback: function(resp){
				if(resp.message){
					frm.refresh_fields('item')
					
					//var table = locals[cdt][cdn].item
					frm.set_query('alternate_item_code', 'item', () => {
						return {
							filters: {
								item_code: ['in',resp.message]
							}
						}
					})
					frm.refresh_fields('item')
				}
				
			}
		})
	}
});

frappe.ui.form.on('Add Alternate Item Details', {
	// refresh: function(frm){
	// 	console.log(">>>:::::::")
	// }
})