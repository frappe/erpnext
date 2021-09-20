// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Delivery Planning', {

	// before_cancel: function(frm){
	// 	console.log(" Cancelling all DPI")
	// 	frm.call({
	// 		method:'on_cancel_all',
	// 		doc: frm.doc,
	// 		callback: function(r){
	// 			if(r.message){
	// 				console.log("==== before save ==========")
	// 			}
	// 		}
				
	// 	});
	// },

	before_save: function(frm){
		if(frm.doc.delivery_date_from > frm.doc.delivery_date_to)
		{ frappe.throw(__('Delivery Date To should be greater or equal to Date From '))}
	},
	onload: function(frm){

		frm.call({
			method:'refresh_status',
			doc: frm.doc,
			callback: function(r){
				if(r.message){
					frm.refresh_field('d_status')
				}
			}
				
		});

		cur_frm.set_query("transporter", function() {
			return {
			   "filters": {
					"is_transporter": 1,
				}
			}
		});

		if( frm.doc.docstatus === 1 && frm.doc.d_status != "Completed"){

//  setting status doccument
		// frm.call({
		// 	method:'refresh_status',
		// 	doc: frm.doc,
		// 	callback: function(r){
		// 		if(r.message){
		// 			frm.refresh_field('d_status')
		// 		}
		// 	}
				
		// });

		// code to show Delivery palnning button
		frm.call({
			method:'check_dpi',
			doc:frm.doc,
			callback: function(r){
				if(r.message){
					frm.set_df_property('show_delivery_planning_item','hidden',1)
					frm.refresh_field('show_delivery_planning_item')
				}
			}
		});

//		code for button visibility on certian condition
		frm.call({
				method : 'check_transporter_po_btn',
				doc: frm.doc,
				callback : function(r){
						if(r.message == 1){
							console.log("11111111111 in side po tr both available",r.message)
							}

						else if(r.message == 2){
							frm.set_df_property('show_purchase_order_planning_item','hidden',1)
							frm.refresh_field('show_purchase_order_planning_item')
							console.log("22222222222222 in side tr both available",r.message)
						}
						else if (r.message == 3){
							frm.set_df_property('show_transporter_planning_item','hidden',1)
							frm.refresh_field('show_transporter_planning_item')
							console.log("333333333333 in side po available",r.message)

						}
						else{
							frm.set_df_property('show_purchase_order_planning_item','hidden',1)
							frm.set_df_property('show_transporter_planning_item','hidden',1)
							frm.refresh_field('show_purchase_order_planning_item')
							frm.refresh_field('show_transporter_planning_item')
							console.log("444444444444 nothing available",r.message)
						}
					}
				});

//	 	code for create and calcluate custom button

		frm.call({
				method : 'check_po_in_dpi',
				doc: frm.doc,
				callback : function(r){
					if(r.message == 1){
						console.log("----- 1 --- --For Both PO and DN -  ---  ---  ",r.message);

							//  custom button to populate Transporter wise Delivery Planning
							frm.add_custom_button(__("Transporter Summary"), function() {

								frm.call({
									method : 'summary_call',
									doc: frm.doc,
									callback : function(r){
										if(r.message == 1){
											console.log("-----  --- --item--  ---  ---  ",r);
											
											frm.refresh();
											// location.reload();
											frappe.msgprint("  Transporter wise Delivery Plan created");
											console.log("msg = 1 create trabsport ")
											frm.reload_doc();	
										}
										else{
										frappe.msgprint(" Unable to create Transporter wise Delivery Plan   ");
										}
								   }
								});
							},__("Calculate"));

							//custom button to generate Purchase Order Planning Items
							console.log("Inside custom if purchase order")
							frm.add_custom_button(__("Purchase Order Summary"), function() {
							frm.call({
								method : 'purchase_order_call',
								doc: frm.doc,

								callback : function(r){
									if(r.message == 1){
											console.log("-----  --- --item--  ---  ---  ",r);
											frappe.msgprint(" Purchase Order Plan Items created  ");
											frm.reload_doc();
										}
									else{
										frappe.msgprint(" Unable to create Purchase Delivery Plan Item   ");
										}
							   }
							});
							},__("Calculate"));

						// custom button Create for Purchase Order Creation
							frm.add_custom_button(__('Purchase Order'), function () {
								frm.call({
									method : 'make_po',
									doc: frm.doc,
									callback : function(r){
										if(r.message == 1){
											console.log("-----  --- --PO Create-  ---  ---  ",r);
											frm.refresh();
											frappe.msgprint("  Purchase Order created ");
											frm.reload_doc();
										}
										else{
											frappe.msgprint(" Purchase Order already created ");
										}
								   }
								});
							}, __('Create'));

							//custom button 'Create' for Pick List
							console.log("Creating CREATE button")
							frm.add_custom_button(__('Pick List'), function () {
								frm.call({
									method : 'make_picklist',
									doc: frm.doc,
									callback : function(r){
										if(r.message == 1){
											console.log("-----  --- --Pick List Create-  ---  ---  ",r);
											frm.refresh();
											// frappe.msgprint(" Pick List created ");
											frm.reload_doc();
										}
										else{
											frappe.msgprint(" Unable to create Pick List ");
										}
								   }
								});
							}, __('Create'));

					//    	Delivery Note creation using custom button
							frm.add_custom_button(__('Delivery Note'), function () {
								frm.call({
									method : 'make_dnote',
									doc: frm.doc,
									callback : function(r){
										if(r.message == 1){
											console.log("-----  --- --Dnote Create-  ---  ---  ",r);
											frappe.msgprint({
											title: __('Delivery Note created'),
											message: __('Created Delivery note using Pick List'),
											indicator: 'green'
										});
										}
										else if(r.message == 2){
											console.log("------- 2  Dnote Create-  ---  ---  ",r);
											frappe.msgprint({
											title: __('Delivery Note created'),
											message: __('Delivery Note Created'),
											indicator: 'green'
											
										});
											frm.reload_doc();
										}
										else{
											frappe.msgprint({
											title: __('Delivery Note not created'),
											message: __('Delivery note already created'),
											indicator: 'blue'
										});
										}
										frm.reload_doc();
								   }
								});
							}, __('Create'));
					}
					else if(r.message == 2){
						console.log("----- 2 --- --FOR Purchase Order -  ---  ---  ",r.message);

							//custom button to generate Purchase Order Planning Items
							console.log("Inside custom if purchase order")
							frm.add_custom_button(__("Purchase Order Summary"), function() {
							frm.call({
								method : 'purchase_order_call',
								doc: frm.doc,

								callback : function(r){
									if(r.message == 1){
											console.log("-----  --- --item--  ---  ---  ",r);
											frm.refresh();
											frappe.msgprint(" Purchase Order Plan Items created  ");
											frm.reload_doc();
										}
									else{
										frappe.msgprint(" Unable to create Purchase Delivery Plan Item   ");
										}
							   }
							});
							},__("Calculate"));

							// custom button Create for Purchase Order Creation
							frm.add_custom_button(__('Purchase Order'), function () {
								frm.call({
									method : 'make_po',
									doc: frm.doc,
									callback : function(r){
										if(r.message == 1){
											console.log("-----  --- --PO Create-  ---  ---  ",r);
											frm.refresh()
											frappe.msgprint("  Purchase Order created ");
											frm.reload_doc();
										}
										else{
											frappe.msgprint(" Purchase Order already created ");
										}
								   }
								});
							}, __('Create'));
						}

					else if(r.message == 3 ){
						console.log("----- 3 --- --Nothing 89977 nothing  ---  ---  ",r.message);

//							Transporter Summary inside Calcluate button
							frm.add_custom_button(__("Transporter Summary"), function() {

								frm.call({
									method : 'summary_call',
									doc: frm.doc,
									callback : function(r){
										if(r.message == 1){
											console.log("-----  --- --item--  ---  ---  ",r);
											frappe.msgprint("  Transporter wise Delivery Plan created  ");
											console.log("msg = 3 create transporter ")
											// location.reload();
											// frm.dirty();
											frm.refresh();
											frm.reload_doc();
											
										}
										else{
										frappe.msgprint(" Unable to create Transporter wise Delivery Plan   ");
										}
								   }
								});
							},__("Calculate"));

							//custom button 'Create' for Pick List
							console.log("Creating CREATE button")
							frm.add_custom_button(__('Pick List'), function () {
								frm.call({
									method : 'make_picklist',
									doc: frm.doc,
									callback : function(r){
										if(r.message == 1){
											console.log("-----  --- --Pick List Create-  ---  ---  ",r);
											frm.reload_doc();
											frappe.msgprint(" Pick List created ");
											frm.reload_doc();
										}
										else{
											frappe.msgprint(" Unable to create Pick List ");
										}
								   }
								});
							}, __('Create'));

							//    	Delivery Note creation using custom button
							frm.add_custom_button(__('Delivery Note'), function () {
								frm.call({
									method : 'make_dnote',
									doc: frm.doc,
									callback : function(r){
										if(r.message == 1){
											console.log("-----  --- --Dnote Create-  ---  ---  ",r);
											frappe.msgprint({
											title: __('Delivery Note created'),
											message: __('Created Delivery note using Pick List'),
											indicator: 'green'
										});frm.reload_doc();
										}
										else if(r.message == 2){
											console.log("-----  --- -- 2  Dnote Create-  ---  ---  ",r);
											frappe.msgprint({
											title: __('Delivery Note created'),
											message: __('Delivery Note Created'),
											indicator: 'green'
										});frm.reload_doc();
										}
										else{
											frappe.msgprint({
											title: __('Delivery Note not created'),
											message: __('Delivery Note already created'),
											indicator: 'orange'
										});
										}
								   }
								});
							}, __('Create'));
					}
					else{
						console.log("----- 4 --- --Nothing 85068 89977 available-  ---  ---  ",r.message);
						console.log("----- 4 --- --Nothing 85068 89977 available-  ---  ---  ",r.dpi_dn);
					}
			   }
		});
		}
    },
	delivery_date_from: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.delivery_date_from
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("delivery_date_from_nepal", resp.message)
				}
			}
		})
	},
	delivery_date_to: function (frm) {
		frappe.call({
			method: "erpnext.nepali_date.get_converted_date",
			args: {
				date: frm.doc.delivery_date_to
			},
			callback: function (resp) {
				if (resp.message) {
					cur_frm.set_value("deliver_date_to_nepal", resp.message)
				}
			}
		})
	},



	 refresh: function(frm) {

		// if (frm.doc.d_status == "Completed"){
		// 	// frm.remove_custom_button('Pick List','Create');
		// 	frm.clear_custom_buttons();
			
		// }

		if (frm.doc.docstatus === 1 && frm.doc.d_status != "Pending Planning"){
			frm.add_custom_button(__("Gantt Chart"), function () {
				frappe.route_options = {
					"related_delivey_planning": frm.doc.name,
					"docstatus":1
				};
				frappe.set_route("List", "Delivery Planning Item", "Gantt");
			});
		};

		document.getElementByClass("icon icon-sm").style.display = "none";

	},

		show_delivery_planning_item: function(frm) {

			frappe.route_options = {"related_delivey_planning": frm.doc.docname };
			frappe.set_route("Report","Delivery Planning Item", {
   				"related_delivey_planning": frm.doc.name
			});
		},

		show_transporter_planning_item: function(frm) {

			frappe.route_options = {"related_delivery_planning": frm.doc.docname };
			frappe.set_route("Report", "Transporter Wise Planning Item", {
   				"related_delivery_planning": frm.doc.name
			});
		},

		show_purchase_order_planning_item: function(frm) {

			frappe.route_options = {"related_delivery_planning": frm.doc.docname };
			frappe.set_route("Report", "Purchase Orders Planning Item", {
   				"related_delivery_planning": frm.doc.name
			});
		},

	
});
