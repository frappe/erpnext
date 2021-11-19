// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Delivery Planning Item', {
	
	refresh : function(frm){
		if(frm.doc.docstatus != 1){
			frm.call({
						doc:frm.doc,
						method: 'update_stock',
						callback: function(r){
							if(r.message){
								console.log("Item stock Updated")
							}
						}
					});
		}
	},
	

	sorce_warehouse: function(frm){
		if(frm.doc.docstatus != 1){
			console.log("Inside soure_warehouse")
			frm.call({
						doc:frm.doc,
						method: 'update_stock',	
						callback: function(r){
							if(r.message)
							frm.doc.current_stock = r.message.projected_qty
							frm.refresh_field("current_stock");
							frm.doc.available_stock = r.message.actual_qty
							frm.refresh_field("available_stock")
							
						}
					});
		}
	},

	validate : function(frm) {
		if (frm.doc.customer && frm.doc.qty_to_deliver && frm.doc.uom && frm.doc.item_name){
			frm.doc.full_dname = frm.doc.customer+ " " + frm.doc.item_name + " " + frm.doc.qty_to_deliver + " " + frm.doc.uom
		}
	},

	qty_to_deliver: function(frm){
		if(frm.doc.qty_to_deliver > frm.doc.ordered_qty)
		{
			frappe.throw(__('qty is greater than ordered qty'))
		}
		else{
			console.log("qty_to_deliver",frm.doc.qty_to_deliver)
			frm.set_value({
				pending_qty: frm.doc.ordered_qty - frm.doc.qty_to_deliver ,
				weight_to_deliver: frm.doc.qty_to_deliver * frm.doc.weight_per_unit 
			})
		}
	},

	onload: function(frm){

		if(frm.doc.docstatus != 1){
					frm.call({
								doc:frm.doc,
								method: 'update_stock',
								callback: function(r){
									if(r.message){
										console.log("Item stock Updated")
									}
								}
							});
				}

		cur_frm.set_query("transporter", function() {
			return {
			   "filters": {
					"is_transporter": 1,
				}
			}
		});

		if( frm.doc.docstatus > 0 )	{
			console.log("frm.docstatus")
			frm.set_df_property('split','hidden',1)
			frm.refresh_field("split")
		}
		
		
	},


	split: function(frm) {
			var new_supplier;
			var new_warehouse;
			var new_transporter;
			var new_date;

			if(frm.doc.docstatus == 1){
				
				frappe.msgprint({
				title: __('Notification'),
				indicator: 'red',
				message: __('Cannot Split Submitted Document')
				});
			}
			else if(frm.doc.docstatus == 2){
				
				frappe.msgprint({
				title: __('Notification'),
				indicator: 'red',
				message: __('Cannot Split Cancelled Document')
				});
			}
			else{	
			let d = new frappe.ui.Dialog({
			title: 'Split Planning Item',
			fields: [
				{
					label: 'Transporter',
					fieldname: 'transporter',
					fieldtype: 'Link',
				    options: "Supplier",
				   
				    depends_on: "eval: doc.supplier_dc == 0",
					mandatory_depends_on : "eval: doc.supplier_dc == 0",
					onchange: function() {
						frappe.model.get_value('Supplier', {"name":d.fields_dict.transporter.value}, 'supplier_name',
						function(dd){								
						console.log(" a000000",dd.supplier_name)
							if (d.fields_dict.transporter.value){
								d.fields_dict.transporter_name.value = dd.supplier_name;
								d.fields_dict.transporter_name.refresh();
							}
							else{
								d.fields_dict.transporter_name.value = "Please select Transporter";
								d.fields_dict.transporter_name.refresh();
							}
						})
					},

				},
				{
					label: 'Transporter Name',
					fieldname: 'transporter_name',
					fieldtype: 'Data',
					read_only: 1,
					depends_on: "eval: doc.supplier_dc == 0",
					mandatory_depends_on : "eval: doc.supplier_dc == 0",
					default: "Please select Transporter"
				},
				{
					label: 'Deliver Date',
					fieldname: 'delivery_date',
					fieldtype: 'Date',
					reqd: 1
				},
				{
					label: 'Current Qty To Deliver',
					fieldname: 'qty_td',
					fieldtype: 'Float',
					default : frm.doc.qty_to_deliver,
					read_only: 1
				},
				{
					label: 'Current Pending Qty',
					fieldname: 'qty_pd',
					fieldtype: 'Float',
					default : frm.doc.pending_qty,
					read_only: 1
				},
				{
					label: 'New Qty To Deliver',
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
					default: frm.doc.sorce_warehouse

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
					onchange: function() {
						frappe.model.get_value('Supplier', {"name":d.fields_dict.supplier.value}, 'supplier_name',
						function(dd){		
							if (d.fields_dict.supplier.value){						
							d.fields_dict.supplier_name.value = dd.supplier_name
							d.fields_dict.supplier_name.refresh();
							}
							else{
								d.fields_dict.supplier_name.value = "Please select Supplier";
								d.fields_dict.supplier_name.refresh();
							}
						})
					},
				},
				{
					label: 'Supplier Name',
					fieldname: 'supplier_name',
					fieldtype: 'Data',
					depends_on: "eval: doc.supplier_dc == 1 ",
					mandatory_depends_on : "eval: doc.supplier_dc == 1",
					read_only: 1,
					default: "Please select Supplier"
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
			// d.show();

		}
});



