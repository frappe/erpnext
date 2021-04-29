// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// Copyright (c) 2021, Dexciss Technology and contributors
// For license information, please see license.txt

frappe.ui.form.on('Additional Item', {
	work_order: function(frm){
		frappe.call({
			doc: frm.doc,
			method: 'bom_wise_item',
			callback: function(resp){
				frm.fields_dict['items'].grid.get_field('item').get_query = function(doc, cdt, cdn) {
					var child = locals[cdt][cdn];
					return {    
						filters:[
							['item_code', 'in', resp.message]
						]
					}
				}
			}
		})
		frappe.call({
			doc: frm.doc,
			method: 'get_job_card',
			callback: function(resp){
				if(!resp.exec){
					frm.set_query("job_card", function() {
						return {
							"filters": {
								'name': ['in',resp.message]
							}
						};
					})
				}
			}
		})
	}
});

frappe.ui.form.on('Additional Items Detail', {
	item: function(frm,cdt,cdn){
		var table = locals[cdt][cdn]
		if(table.item){
			frappe.call({
				method: "erpnext.manufacturing.doctype.additional_item.additional_item.get_item_data",
				// method: "get_item_data",
				args: {
					"item": table.item,
					"wo": frm.doc.work_order,
				},
				callback: function(resp){
					if(resp.message){
					table.item_name = resp.message[0].item_name
					table.uom = resp.message[0].weight_uom
					table.current_stock = resp.message[0].qty
					table.weight_per_unit = resp.message[0].weight_per_unit
					}
					frm.refresh_field('items')
				}
			})
		}
	}
});

