// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

// Copyright (c) 2021, Dexciss Technology and contributors
// For license information, please see license.txt

frappe.ui.form.on('Additional Item', {
	onload_post_render: function(frm){
		frm.add_custom_button(__('Add Alternate Item'),function() {

			erpnext.utils.select_alternate_items({
                frm: frm,
                child_docname: "items",
                warehouse_field: "source_warehouse",
                child_doctype: "Additional Items Details",
                original_item_field: "original_item",
                condition: (d) => {
                    if (d.allow_alternative_item) {return true;}
                }
            });

			// var mdata = []
			// const dialog = new frappe.ui.Dialog({
			// 	title: __("Select Alternate Item"),
			// 	fields: [
			// 		{fieldtype:'Section Break', label: __('Items')},
			// 		{
			// 			fieldname: "alternative_items", fieldtype: "Table", cannot_add_rows: true,
			// 			in_place_edit: true, data: mdata,
			// 			get_data: () => {
			// 				console.log("***>>>")
			// 				return [{'wo_item':'RM-00367'}];
			// 			},
			// 			fields: [{
			// 				fieldtype:'Data',
			// 				fieldname:"docname",
			// 				hidden: 1
			// 			}, {
			// 				fieldtype:'Link',
			// 				fieldname:"wo_item",
			// 				options: 'Item',
			// 				in_list_view: 1,
			// 				read_only: 1,
			// 				label: __('Work Order Item'),
			// 				// get_data: () => {
				
			// 				// 	return [{'wo_item':'RM-00367'}];
			// 				// },
			// 			}, {
			// 				fieldtype:'Data',
			// 				fieldname:"item_name",
			// 				in_list_view: 1,
			// 				label: __('Item Name'),
			// 				// onchange: function() {
			// 				// 	const item_code = this.get_value();
			// 				// 	const warehouse = this.grid_row.on_grid_fields_dict.warehouse.get_value();
			// 				// 	if (item_code && warehouse) {
			// 				// 		frappe.call({
			// 				// 			method: "erpnext.stock.utils.get_latest_stock_qty",
			// 				// 			args: {
			// 				// 				item_code: item_code,
			// 				// 				warehouse: warehouse
			// 				// 			},
			// 				// 			callback: (r) => {
			// 				// 				this.grid_row.on_grid_fields_dict
			// 				// 					.actual_qty.set_value(r.message || 0);
			// 				// 			}
			// 				// 		})
			// 				// 	}
			// 				// },
			// 				// get_query: (e) => {
			// 				// 	return {
			// 				// 		query: "erpnext.stock.doctype.item_alternative.item_alternative.get_alternative_items",
			// 				// 		filters: {
			// 				// 			item_code: e.item_code
			// 				// 		}
			// 				// 	};
			// 				// }
			// 			}, {
			// 				fieldtype:'Data',
			// 				fieldname:"description",
			// 				in_list_view: 1,
			// 				label: __('Description'),
			// 				// onchange: function() {
			// 				// 	const warehouse = this.get_value();
			// 				// 	const item_code = this.grid_row.on_grid_fields_dict.item_code.get_value();
			// 				// 	if (item_code && warehouse) {
			// 				// 		frappe.call({
			// 				// 			method: "erpnext.stock.utils.get_latest_stock_qty",
			// 				// 			args: {
			// 				// 				item_code: item_code,
			// 				// 				warehouse: warehouse
			// 				// 			},
			// 				// 			callback: (r) => {
			// 				// 				this.grid_row.on_grid_fields_dict
			// 				// 					.actual_qty.set_value(r.message || 0);
			// 				// 			}
			// 				// 		})
			// 				// 	}
			// 				// },
			// 			}, 
			// 			{
			// 				fieldtype:'Select',
			// 				fieldname:"alternate_item",
			// 				options: 'Item',
			// 				in_list_view: 1,
			// 				label: __('Alternate Item')
			// 			},
			// 			{
			// 				fieldtype:'Select',
			// 				fieldname:"alternate_item",
			// 				options: 'Item',
			// 				in_list_view: 1,
			// 				label: __('Alternate Item')
			// 			}]
			// 		},
			// 	],
			// 	primary_action: function() {
			// 		const args = this.get_values()["alternative_items"];
			// 		const alternative_items = args.filter(d => {
			// 			if (d.alternate_item && d.item_code != d.alternate_item) {
			// 				return true;
			// 			}
			// 		});
		
			// 		alternative_items.forEach(d => {
			// 			let row = frappe.get_doc(opts.child_doctype, d.docname);
			// 			let qty = null;
			// 			if (row.doctype === 'Work Order Item') {
			// 				qty = row.required_qty;
			// 			} else {
			// 				qty = row.qty;
			// 			}
			// 			row[item_field] = d.alternate_item;
			// 			frm.script_manager.trigger(item_field, row.doctype, row.name)
			// 				.then(() => {
			// 					frappe.model.set_value(row.doctype, row.name, 'qty', qty);
			// 					frappe.model.set_value(row.doctype, row.name,
			// 						opts.original_item_field, d.item_code);
			// 				});
			// 		});
		
			// 		refresh_field(opts.child_docname);
			// 		this.hide();
			// 	},
			// 	primary_action_label: __('Update')
			// });
			// dialog.show();

		})
	},
	work_order: function(frm){
		//set_filter_to_item(frm)
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
	},
	refresh: function(frm,cdt,cdn){
		var item_table = locals[cdt][cdn].items
		if(item_table.length > 0){
			frm.add_custom_button(__("Add Alternate Item"), ()=> {
				frappe.new_doc("Add Alternate Item", {'add_additional_item':frm.doc.name})
			})
		}

		if(frm.doc.work_order){
			//set_filter_to_item(frm)
		}
	}
});

function set_filter_to_item(frm){
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
}
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

