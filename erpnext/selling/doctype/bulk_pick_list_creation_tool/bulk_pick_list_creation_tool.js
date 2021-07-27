// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Pick List Creation Tool', 
{

	onload: function(frm)
	{
         frappe.call({
			method: "get_options",
			doc: frm.doc,
			callback: function(r) {
				frm.set_df_property("series", "options", r.message);
			}
		});
    },
    refresh: function(frm, dt, dn) 
    {
	    frm.disable_save();
		frm.page.set_primary_action(__('Create Pick List'), () => {
			let btn_primary = frm.page.btn_primary.get(0);
			return frm.call({
				doc: frm.doc,
				freeze: true,
				btn: $(btn_primary),
				method: "make_pick_list",
				freeze_message: __("Creating  Pick Lists"),
				callback: (r) => {
					if(!r.exc){
						frappe.msgprint(__("Pick List Created"));
						frm.clear_table("items");
						frm.clear_table("item");
						frm.refresh_fields();
						frm.reload_doc();
					}
				}
			});
		});
		frm.cscript.get_items = function() 
		{
			frm.call({
				doc:frm.doc,
				method: 'get_item',
                callback:function(r){
                	if(r.message && frm.doc.purpose === "Delivery"){
                		frm.clear_table("items")
                		$.each(r.message,function(index,row){
                			if(row.qty>0){
	                			var d = frm.add_child("items");
	                            d.customer=row.customer
	                            d.customer_name = row.customer_name
	                            d.item_code = row.item_code
	                            d.item_name = row.item_name
	                            d.description = row.description
	                            d.item_group = row.item_group
	                            d.warehouse = row.warehouse
	                            d.qty = row.qty
	                            d.stock_qty = row.stock_qty
	                            d.uom = row.uom
	                            d.conversion_factor = row.conversion_factor
	                            d.stock_uom = row.stock_uom
	                            d.sales_order = row.name
	                            d.sales_order_item = row.soi_item
	                            frm.refresh_field("items")
	                        }
                        })
                	}
					if(r.message && frm.doc.purpose === "Material Transfer for Manufacture"){
						frm.refresh_field("item")
					}
                }
			});
		}

//         frm.add_custom_button(__('Sales Order'),function() 
//         {
//             erpnext.utils.map_current_doc({
// 				method: 'nextsales.next_sales.doctype.bulk_pick_list_creation_tool.bulk_pick_list_creation_tool.create_pick_list',
// 				source_doctype: 'Sales Order',
// 				target: frm,
// 				setters: {
// //					company: frm.doc.company || undefined,
// 					customer: frm.doc.customer || undefined,
//                     customer_name: frm.doc.customer_name || undefined,
//                     customer_group: frm.doc.customer_group || undefined,
// 				},
// 				date_field: 'transaction_date',
// 				get_query_filters: {
//                                     docstatus: 1,
//                                     per_delivered: ['<', 100],
//                                     status: ['!=', ''],
//                                     customer: frm.doc.customer
//                                 }
// 			});
//         }, __("Get items from"));
	},
	company: function(frm){
		set_filter_to_parent_warehouse(frm)
	}
});

function set_filter_to_parent_warehouse(frm){
	frm.set_query('parent_warehouse', function(doc) {
		return {
			filters: {
				"is_group": 1,
				"company": frm.doc.company
			}
		};
	});
}

