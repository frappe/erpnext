// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Delivery Planning Item', {


	// save: function(frm){
	// 	if(frm.doc.approved )
	// 		{
	// 			frm.set_df_property('transporter','read_only',1)
	// 			frm.set_df_property('sorce_warehouse','read_only',1)
	// 			frm.set_df_property('qty_to_deliver','read_only',1)
	// 			frm.set_df_property('approved','read_only',1)
	// 			frm.set_df_property('supplier_dc','read_only',1)
	// 			frm.set_df_property('supplier','read_only',1)
	// 			frm.set_df_property('split','hidden',1)
	// 			frm.refresh_field("transporter")
	// 			frm.refresh_field("sorce_warehouse")
	// 			frm.refresh_field("qty_to_deliver")
	// 			frm.refresh_field("supplier_dc")
	// 			frm.refresh_field("approved")
	// 			frm.refresh_field("supplier")
	//             frm.refresh_field("split")
	// 		}
	// },

	// refresh: function(frm){
	// 	frm.call({
	// 		doc:frm.doc,
	// 		method: 'update_stock',
			
	// 	});
	// },
	
	before_load: function(frm){
		if (!frm.doc.approved)
		frm.call({
					doc:frm.doc,
					method: 'update_stock',
					
				});

	},

	onload: function(frm){
		// if(frm.transporter){
		// 	frm.set_df_property('supplier_dc','hidden',1)
		// 	frm.refresh_field("supplier_dc")
		// }
		// else{
		// 	frm.set_df_property('supplier_dc','hidden',0)
		// 	frm.refresh_field("supplier_dc")
		// }


		// if (!frm.doc.approved)
		// frm.call({
		// 			doc:frm.doc,
		// 			method: 'update_stock',
					
		// 		});
				

		// if(frm.doc.approved)
		// 	{
		// 		frm.set_df_property('transporter','read_only',1)
		// 		frm.set_df_property('sorce_warehouse','read_only',1)
		// 		frm.set_df_property('qty_to_deliver','read_only',1)
		// 		frm.set_df_property('approved','read_only',1)
		// 		frm.set_df_property('supplier_dc','read_only',1)
		// 		frm.set_df_property('supplier','read_only',1)
		// 		frm.refresh_field("transporter")
		// 		frm.refresh_field("sorce_warehouse")
		// 		frm.refresh_field("qty_to_deliver")
		// 		frm.refresh_field("supplier_dc")
		// 		frm.refresh_field("approved")
		// 		frm.refresh_field("supplier")
	    //     };

		if (frm.doc.approved)
			{
				frm.set_df_property('split','hidden',1)
				frm.refresh_field("split")
			}	
		else if(frm.doc.ordered_qty > 1)
			{
				frm.set_df_property('split','hidden',0)
				frm.refresh_field("split")
			}
		
	},


	split: function(frm) {
			var new_supplier;
			var new_warehouse;
			var new_transporter;
			var new_date;
			let d = new frappe.ui.Dialog({
			title: 'Split Planning Item',
			fields: [
				{
					label: 'Transporter',
					fieldname: 'transporter',
					fieldtype: 'Link',
				    options: "Supplier",
				    default: frm.doc.transporter,
				    depends_on: "eval: doc.supplier_dc == 0",
					mandatory_depends_on : "eval: doc.supplier_dc == 0",

				},
				{
					label: 'Deliver Date',
					fieldname: 'delivery_date',
					fieldtype: 'Date',
					reqd: 1
				},
				{
					label: 'Qty To Deliver',
					fieldname: 'qty',
					fieldtype: 'Float',
					default : 1,
					reqd: 1
				},
				{
					label: 'Source Warehouse',
					fieldname: 'src_warehouse',
					fieldtype: 'Link',
					options: "Warehouse",
					depends_on: "eval: doc.supplier_dc == 0",

				},
				{
					label: 'Supplier delivers to Customer ',
					fieldname: 'supplier_dc',
					default: frm.doc.supplier_dc,
					fieldtype: 'Check'
				},
				{
					label: 'Supplier',
					fieldname: 'supplier',
					fieldtype: 'Link',
					options: "Supplier",
					depends_on: "eval: doc.supplier_dc == 1 ",
					mandatory_depends_on : "eval: doc.supplier_dc == 1",
				}
			],

			primary_action_label: 'Submit',
			primary_action(values) {
				console.log(values);
				if(values.transporter)
				{ new_transporter = values.transporter;
					console.log("0000000110000000",new_transporter);
				}
				
				else{ new_transporter = "";
					console.log("0000000011000000",new_transporter);
				}
				if(values.supplier)
				{ new_supplier = values.supplier;
					console.log("00000000000000",new_supplier);
				}
				
				else{ new_supplier = "";
					console.log("00000000000000",new_supplier);
				}

				if(values.src_warehouse)
				{ new_warehouse = values.src_warehouse;
					console.log("0000000110000000",new_warehouse);
				}
				
				else{ new_warehouse = "";
					console.log("0000000011000000",new_warehouse);
				}

				if(values.qty == 0 || values.qty >= frm.doc.qty_to_deliver)
				{
					frappe.msgprint({
						title: __('Warning'),
						indicator: 'red',
						message: __('Qty To Deliver should be greater than 0 or  less than Item selected to split')
						});
					
					// frappe.throw(__('Qty to delivery should be geater than 0 and less than {0}').format(self.qty_to_deliver))
				
				}
				else {			
					frm.call({
					doc:frm.doc,
					method: 'split_dp_item',
					args: {
							n_transporter : new_transporter,
							n_qty : values.qty,
							n_src_warehouse : new_warehouse,
							n_supplier_dc : values.supplier_dc,
							n_supplier : new_supplier,
							n_date : values.delivery_date
						  },

					callback: function(r){
						if(r.message){
							console.log("item",r);
							frappe.msgprint({
								title: __('Notification'),
								indicator: 'green',
								message: __('Document updated successfully')
								});
								d.hide();
								// frappe.set_route("Report", "Delivery Planning Item");
								// frappe.route_options = {"related_delivery_planning": frm.doc.related_delivey_planning };
								frappe.set_route("List","Delivery Planning Item", {
									"related_delivey_planning": frm.doc.related_delivey_planning
								});
						}
						else{
							frappe.msgprint({
							title: __('Notification'),
							indicator: 'red',
							message: __('Document update failed')
							
							});
							d.hide();
						}
					}
				});
				}

				
				
			}
			});

			d.show();

		}
});

// frappe.ui.form.on("Delivery Planning Item", "onload", function(frm) {
// 	console.log(" in side split button",frm.doc.ordered_qty)
// 	if (frm.doc.approved)
// 		{
// 			frm.set_df_property('split','hidden',1)
// 	        frm.refresh_field("split")
// 		}	
// 	else if(frm.doc.ordered_qty > 1)
// 		{
// 			frm.set_df_property('split','hidden',0)
// 			frm.refresh_field("split")
// 		}

// });

frappe.ui.form.on("Delivery Planning Item", "onload", function(frm) {
    cur_frm.set_query("transporter", function() {
        return {
           "filters": {
                "is_transporter": 1,
            }
        }
    });
});


