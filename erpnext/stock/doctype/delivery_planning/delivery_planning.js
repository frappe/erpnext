// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Delivery Planning', {

	 onload: function(frm){


//		frappe.ui.form.on("Transporter", {
//			setup: function(frm) {
//				frm.set_query("transporter", function() {
//					return {
//						filters: [
//							["is_transporter" = 1]
//						]
//					}
//				});
//			}
//		});

////	 To fetch pin code from Address and set in Postal code from and to
//	 	console.log("--------------000000000---------------")
//         frappe.call({
//			method: "get_options",
//			doc: frm.doc,
//			callback: function(r) {
//			console.log("this is option",r.message)
//				frm.set_df_property("pincode_from", "options", r.message);
//				frm.refresh_field('pincode_from');
//				frm.set_df_property("pincode_to", "options", r.message);
//				frm.refresh_field('pincode_to');
//			}
//		});
//   		frappe.call({
//   			method: "get_transport",
//   			doc: frm.doc,
//   			callback: function(r){
//   			if(r.message)
//   			console.log("000000000011111111111",r)
//   				frm.set_df_property("transporter","link",r.message);
//   			}
//
//   		});

    },

//    on_submit: funtion(frm){
//
//    },

	 refresh: function(frm) {

//	 if (frm.docstatus === 1)
//	 	{
//	 	frm.add_custom_button(__("Create Pick List"), function()  {
////	 		return frm.call({
////				doc: frm.doc,
////				freeze: true,
////				btn: $(btn_primary),
////				method: "make_pick_list",
////				freeze_message: __("Creating Pick Lists"),
////				callback: (r) => {
////					if(!r.exc){
////						frappe.msgprint(__("Pick List Created"));
////						frm.clear_table("items");
////						frm.clear_table("item");
////						frm.refresh_fields();
////						frm.reload_doc();
////					}
////				}
////			});
//
//   		 });
//	 	}

//	frm.cscript.get_sales_orders = function()
//		{
//			frm.call({
//				doc:frm.doc,
//				method: 'get_sales_order',
//                callback:function(r){
//                	if(r.message){
//                		console.log("transport",r);
//                		$.each(r.message,function(index,row){
//                			if(row.qty>0){
//	                			var d = frm.add_child("item_wise_dp");
//	                			d.transporter = row.transporter
// 	                            d.customer = row.customer
//	                            d.item = row.item_code
//	                            d.item_name = row.item_name
//	                            d.src_warehouse = row.warehouse
//	                            d.a_qty = row.qty
//	                            d.o_qty = row.stock_qty
//	                            d.sales_order = row.name
//	                            d.weight_od = d.o_qty * row.weight_per_unit
//	                            d.a_stock = row.projected_qty - row.qty
//	                            d.d_date = row.delivery_date
//	                            d.c_stock = row.projected_qty
//	                            d.p_qty = d.o_qty - d.qty_tbd
//	                            d.weight_pu = row.weight_per_unit
//	                            frm.set_df_property('item_wise_dp','hidden',0)
//	                            frm.refresh_field("item_wise_dp")
//	                        }
//                        })
//                	}
//                }
//			});
//		}
//
//	frm.cscript.get_daily_dp = function()
//		{
//			frm.call({
//				doc:frm.doc,
//				method: 'get_daily_d',
//                callback:function(r){
//                	if(r.message){
//                		console.log("order",r);
//                		$.each(r.message,function(index,row){
//                			if(row.total_net_weight>0){
//	                			var d = frm.add_child("transporter_wise_dp");
//	                			console.log("order",row.transporter);
//	                			d.transporter = row.transporter
////	                            d.s_warehouse = row.warehouse
//	                            d.qty_td = row.total_qty
//	                            d.weight_od = row.total_net_weight
////	                            d.weight_od = d.qty_td * row.weight_per_unit
//	                            d.d_date = row.delivery_date
////	                            var weight_pu = row.weight_per_unit
//	                            frm.set_df_property('transporter_wise_dp','hidden',0)
//	                            frm.refresh_field("transporter_wise_dp")
//	                        }
//                        })
//                	}
//                }
//			});
//		}
//
//	frm.cscript.po_to_create = function()
//		{
//			frm.call({
//				doc:frm.doc,
//				method: 'p_order_create',
//                callback:function(r){
//                	if(r.message){
//                		console.log("item",r);
//                		$.each(r.message,function(index,row){
//                			if(row.qty>0){
//	                			var d = frm.add_child("orderw_pplan");
//	                			d.supplier = row.transporter
//	                            d.item_code = row.item_code
//	                            d.item_name = row.item_name
//	                            d.src_warehouse = row.warehouse
//	                            d.qty_to = row.qty
//	                            d.o_qty = row.stock_qty
//	                            d.sales_order = row.name
//
//	                            frm.set_df_property('orderw_pplan','hidden',0)
//	                            frm.refresh_field("orderw_pplan")
//	                        }
//                        })
//                	}
//                }
//			});
//
//		}



	},

		show_delivery_planning_item: function(frm) {

			frappe.route_options = {"related_delivery_planning": frm.doc.docname };
			frappe.set_route("Report", "Delivery Planning Item", {
   				"related_delivey_planning": frm.doc.name
			});
		},

		show_transporter_planning_item: function(frm) {

			frappe.route_options = {"related_delivery_planning": frm.doc.docname };
			frappe.set_route("Form", "Transporter Wise Planning Item", {
   				"related_delivey_planning": frm.doc.name
			});
		},

		show_purchase_order_planning_item: function(frm) {

			frappe.route_options = {"related_delivery_planning": frm.doc.docname };
			frappe.set_route("Form", "Purchase Orders Planning Item", {
   				"related_delivey_planning": frm.doc.name
			});
		},




});

//frappe.ui.form.on("Item wise Delivery Planning", {
//	qty_tbd: function(frm,cdt,cdn) {
//		var row = locals[cdt][cdn];
//		if (row.qty_tbd)
//			row.p_qty = row.o_qty - row.qty_tbd;
//			row.weight_od = row.weight_pu * row.qty_tbd;
//			refresh_field("weight_od",cdn,"item_wise_dp")
//			refresh_field("p_qty",cdn,"item_wise_dp");
//
//	},
//});

frappe.ui.form.on("Show Delivery Planning Item", {
	show_delivery_planning_item: function(frm) {
		frappe.set_route("Form", "Delivery Planning Item", {
   		"related_delivey_planning": frm.doc.docname
	});
	},
});

frappe.ui.form.on("Delivery Planning", "onload", function(frm) {
    cur_frm.set_query("transporter", function() {
        return {
           "filters": {
                "is_transporter": 1,
            }
        }
    });
});



