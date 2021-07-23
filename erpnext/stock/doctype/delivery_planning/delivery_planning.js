// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Delivery Planning', {

	 onload: function(frm){
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

		if( frm.doc.docstatus === 1){

//		frm.call('refresh_status')
		frm.call({
			method:'refresh_status',
			doc: frm.doc,
			callback: function(r){
				if(r.message){
					frm.refresh_field('d_status')
				}
			}
				
		});

		// code to show Delivery palnning button
		frm.call({
			method:'check_dpi',
			doc:frm.doc,
			callback: function(r){
				if(r.message){
					frm.set_df_property('show_delivery_planning_item','hidden',1)
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
							console.log("22222222222222 in side tr both available",r.message)
						}
						else if (r.message == 3){
							frm.set_df_property('show_transporter_planning_item','hidden',1)
							console.log("333333333333 in side po available",r.message)

						}
						else{
							frm.set_df_property('show_purchase_order_planning_item','hidden',1)
							frm.set_df_property('show_transporter_planning_item','hidden',1)
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
											frappe.msgprint("  Transporter wise Delivery Plan created  ");
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
											frappe.msgprint("  Purchase Order created ");
										}
										else{
											frappe.msgprint(" Unable to create Purchase Order ");
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
											console.log("-----  --- --PO Create-  ---  ---  ",r);
											frappe.msgprint("  Purchase Pick List created ");
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
											console.log("-----  --- -- 2  Dnote Create-  ---  ---  ",r);
											frappe.msgprint({
											title: __('Delivery Note created'),
											message: __('Created Delivery Note using Sales Order'),
											indicator: 'green'
										});
										}
										else{
											frappe.msgprint({
											title: __('Delivery Note not created'),
											message: __('No Items with of this Delivery Planning is Approved or Pick not created'),
											indicator: 'orange'
										});
										}
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
											frappe.msgprint(" Purchase Order Plan Items created  ");
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
											frappe.msgprint("  Purchase Order created ");
										}
										else{
											frappe.msgprint(" Unable to create Purchase Order ");
										}
								   }
								});
							}, __('Create'));



						}

					else if(r.message == 3 ){
						console.log("----- 3 --- --Nothing 85068 89977 nothing  ---  ---  ",r.message);

//							Transporter Summary inside Calcluate button
							frm.add_custom_button(__("Transporter Summary"), function() {

								frm.call({
									method : 'summary_call',
									doc: frm.doc,
									callback : function(r){
										if(r.message == 1){
											console.log("-----  --- --item--  ---  ---  ",r);
											frappe.msgprint("  Transporter wise Delivery Plan created  ");
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
											console.log("-----  --- --PO Create-  ---  ---  ",r);
											frappe.msgprint("  Purchase Pick List created ");
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
											console.log("-----  --- -- 2  Dnote Create-  ---  ---  ",r);
											frappe.msgprint({
											title: __('Delivery Note created'),
											message: __('Created Delivery Note using Sales Order'),
											indicator: 'green'
										});
										}
										else{
											frappe.msgprint({
											title: __('Delivery Note not created'),
											message: __('No Items with of this Delivery Planning is Approved or Pick not created'),
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



	 refresh: function(frm) {
		// 		//status update
		// frm.call({
		// 	method:'refresh_status',
		// 	doc: frm.doc

		// });

		// frm.set('status','To Deliver')
//	if(frm.doc.docstatus === 1)
//	{
//
//    	//  custom button to populate Transporter wise Delivery Planning
//    	frm.add_custom_button(__("Transporter Summary"), function() {
//
//			frm.call({
//				method : 'summary_call',
//				doc: frm.doc,
//				callback : function(r){
//					if(r.message == 1){
//						console.log("-----  --- --item--  ---  ---  ",r);
//						frappe.msgprint("  Transporter wise Delivery Plan created  ");
//					}
//					else{
//					frappe.msgprint(" Unable to create Transporter wise Delivery Plan   ");
//					}
//			   }
//			});
//    	},__("Calculate"),__("In side"));
//
//		//custom button to generate Purchase Order Planning Items
//    	console.log("Inside custom if purchase order")
//		frm.add_custom_button(__("Purchase Order Summary"), function() {
//		frm.call({
//    		method : 'purchase_order_call',
//    		doc: frm.doc,
//
//			callback : function(r){
//               	if(r.message == 1){
//						console.log("-----  --- --item--  ---  ---  ",r);
//						frappe.msgprint(" Purchase Order Plan Items created  ");
//					}
//				else{
//					frappe.msgprint(" Unable to create Purchase Delivery Plan Item   ");
//					}
//           }
//        });
//    	},__("Calculate"));
//
//
//    	//custom button 'Create' for Pick List
//    	console.log("Creating CREATE button")
//    	frm.add_custom_button(__('Pick List'), function () {
//    		frm.call({
//				method : 'make_picklist',
//				doc: frm.doc,
//				callback : function(r){
//					if(r.message == 1){
//						console.log("-----  --- --PO Create-  ---  ---  ",r);
//						frappe.msgprint("  Purchase Pick List created ");
//					}
//					else{
//						frappe.msgprint(" Unable to create Pick List ");
//					}
//			   }
//			});
//    	}, __('Create'));
//
//
//
////    	Delivery Note creation using custom button
//    	frm.add_custom_button(__('Delivery Note'), function () {
//    		frm.call({
//				method : 'make_dnote',
//				doc: frm.doc,
//				callback : function(r){
//					if(r.message == 1){
//						console.log("-----  --- --Dnote Create-  ---  ---  ",r);
//						frappe.msgprint({
//						title: __('Delivery Note created'),
//						message: __('Created Delivery note using Pick List'),
//						indicator: 'green'
//					});
//					}
//					else if(r.message == 2){
//						console.log("-----  --- -- 2  Dnote Create-  ---  ---  ",r);
//						frappe.msgprint({
//						title: __('Delivery Note created'),
//						message: __('Created Delivery Note using Sales Order'),
//						indicator: 'green'
//					});
//					}
//					else{
//						frappe.msgprint({
//						title: __('Delivery Note not created'),
//						message: __('No Items with of this Delivery Planning is Approved or Pick not created'),
//						indicator: 'orange'
//					});
//					}
//			   }
//			});
//    	}, __('Create'));
//
//	}


	},

		show_delivery_planning_item: function(frm) {

			frappe.route_options = {"related_delivey_planning": frm.doc.docname };
			frappe.set_route("Report", "Delivery Planning Item", {
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

frappe.ui.form.on("Delivery Planning", "onload", function(frm) {
    cur_frm.set_query("transporter", function() {
        return {
           "filters": {
                "is_transporter": 1,
            }
        }
    });
});


//frappe.ui.form.on("Delivery Planning", "onload", function(frm) {
//        frm.call({
//				method : 'check_po_in_dpi',
//				doc: frm.doc,
//				callback : function(r){
//					if(r.message == 1){
//						console.log("----- 1 --- --For Both PO and DN -  ---  ---  ",r.message);
//
//							//  custom button to populate Transporter wise Delivery Planning
//							frm.add_custom_button(__("Transporter Summary"), function() {
//
//								frm.call({
//									method : 'summary_call',
//									doc: frm.doc,
//									callback : function(r){
//										if(r.message == 1){
//											console.log("-----  --- --item--  ---  ---  ",r);
//											frappe.msgprint("  Transporter wise Delivery Plan created  ");
//										}
//										else{
//										frappe.msgprint(" Unable to create Transporter wise Delivery Plan   ");
//										}
//								   }
//								});
//							},__("Calculate"));
//
//							//custom button to generate Purchase Order Planning Items
//							console.log("Inside custom if purchase order")
//							frm.add_custom_button(__("Purchase Order Summary"), function() {
//							frm.call({
//								method : 'purchase_order_call',
//								doc: frm.doc,
//
//								callback : function(r){
//									if(r.message == 1){
//											console.log("-----  --- --item--  ---  ---  ",r);
//											frappe.msgprint(" Purchase Order Plan Items created  ");
//										}
//									else{
//										frappe.msgprint(" Unable to create Purchase Delivery Plan Item   ");
//										}
//							   }
//							});
//							},__("Calculate"));
//
//						// custom button Create for Purchase Order Creation
//							frm.add_custom_button(__('Purchase Order'), function () {
//								frm.call({
//									method : 'make_po',
//									doc: frm.doc,
//									callback : function(r){
//										if(r.message == 1){
//											console.log("-----  --- --PO Create-  ---  ---  ",r);
//											frappe.msgprint("  Purchase Order created ");
//										}
//										else{
//											frappe.msgprint(" Unable to create Purchase Order ");
//										}
//								   }
//								});
//							}, __('Create'));
//
//							//custom button 'Create' for Pick List
//							console.log("Creating CREATE button")
//							frm.add_custom_button(__('Pick List'), function () {
//								frm.call({
//									method : 'make_picklist',
//									doc: frm.doc,
//									callback : function(r){
//										if(r.message == 1){
//											console.log("-----  --- --PO Create-  ---  ---  ",r);
//											frappe.msgprint("  Purchase Pick List created ");
//										}
//										else{
//											frappe.msgprint(" Unable to create Pick List ");
//										}
//								   }
//								});
//							}, __('Create'));
//
//					//    	Delivery Note creation using custom button
//							frm.add_custom_button(__('Delivery Note'), function () {
//								frm.call({
//									method : 'make_dnote',
//									doc: frm.doc,
//									callback : function(r){
//										if(r.message == 1){
//											console.log("-----  --- --Dnote Create-  ---  ---  ",r);
//											frappe.msgprint({
//											title: __('Delivery Note created'),
//											message: __('Created Delivery note using Pick List'),
//											indicator: 'green'
//										});
//										}
//										else if(r.message == 2){
//											console.log("-----  --- -- 2  Dnote Create-  ---  ---  ",r);
//											frappe.msgprint({
//											title: __('Delivery Note created'),
//											message: __('Created Delivery Note using Sales Order'),
//											indicator: 'green'
//										});
//										}
//										else{
//											frappe.msgprint({
//											title: __('Delivery Note not created'),
//											message: __('No Items with of this Delivery Planning is Approved or Pick not created'),
//											indicator: 'orange'
//										});
//										}
//								   }
//								});
//							}, __('Create'));
//
//
//					}
//					else if(r.message == 2){
//						console.log("----- 2 --- --FOR Purchase Order -  ---  ---  ",r.message);
//
//							//custom button to generate Purchase Order Planning Items
//							console.log("Inside custom if purchase order")
//							frm.add_custom_button(__("Purchase Order Summary"), function() {
//							frm.call({
//								method : 'purchase_order_call',
//								doc: frm.doc,
//
//								callback : function(r){
//									if(r.message == 1){
//											console.log("-----  --- --item--  ---  ---  ",r);
//											frappe.msgprint(" Purchase Order Plan Items created  ");
//										}
//									else{
//										frappe.msgprint(" Unable to create Purchase Delivery Plan Item   ");
//										}
//							   }
//							});
//							},__("Calculate"));
//
//							// custom button Create for Purchase Order Creation
//							frm.add_custom_button(__('Purchase Order'), function () {
//								frm.call({
//									method : 'make_po',
//									doc: frm.doc,
//									callback : function(r){
//										if(r.message == 1){
//											console.log("-----  --- --PO Create-  ---  ---  ",r);
//											frappe.msgprint("  Purchase Order created ");
//										}
//										else{
//											frappe.msgprint(" Unable to create Purchase Order ");
//										}
//								   }
//								});
//							}, __('Create'));
//
//
//
//						}
//
//					else if(r.message == 3 ){
//						console.log("----- 3 --- --Nothing 85068 89977 nothing  ---  ---  ",r.message);
//
////							Transporter Summary inside Calcluate button
//							frm.add_custom_button(__("Transporter Summary"), function() {
//
//								frm.call({
//									method : 'summary_call',
//									doc: frm.doc,
//									callback : function(r){
//										if(r.message == 1){
//											console.log("-----  --- --item--  ---  ---  ",r);
//											frappe.msgprint("  Transporter wise Delivery Plan created  ");
//										}
//										else{
//										frappe.msgprint(" Unable to create Transporter wise Delivery Plan   ");
//										}
//								   }
//								});
//							},__("Calculate"));
//
//							//custom button 'Create' for Pick List
//							console.log("Creating CREATE button")
//							frm.add_custom_button(__('Pick List'), function () {
//								frm.call({
//									method : 'make_picklist',
//									doc: frm.doc,
//									callback : function(r){
//										if(r.message == 1){
//											console.log("-----  --- --PO Create-  ---  ---  ",r);
//											frappe.msgprint("  Purchase Pick List created ");
//										}
//										else{
//											frappe.msgprint(" Unable to create Pick List ");
//										}
//								   }
//								});
//							}, __('Create'));
//
//							//    	Delivery Note creation using custom button
//							frm.add_custom_button(__('Delivery Note'), function () {
//								frm.call({
//									method : 'make_dnote',
//									doc: frm.doc,
//									callback : function(r){
//										if(r.message == 1){
//											console.log("-----  --- --Dnote Create-  ---  ---  ",r);
//											frappe.msgprint({
//											title: __('Delivery Note created'),
//											message: __('Created Delivery note using Pick List'),
//											indicator: 'green'
//										});
//										}
//										else if(r.message == 2){
//											console.log("-----  --- -- 2  Dnote Create-  ---  ---  ",r);
//											frappe.msgprint({
//											title: __('Delivery Note created'),
//											message: __('Created Delivery Note using Sales Order'),
//											indicator: 'green'
//										});
//										}
//										else{
//											frappe.msgprint({
//											title: __('Delivery Note not created'),
//											message: __('No Items with of this Delivery Planning is Approved or Pick not created'),
//											indicator: 'orange'
//										});
//										}
//								   }
//								});
//							}, __('Create'));
//					}
//					else{
//						console.log("----- 4 --- --Nothing 85068 89977 available-  ---  ---  ",r.message);
//						console.log("----- 4 --- --Nothing 85068 89977 available-  ---  ---  ",r.dpi_dn);
//					}
//			   }
//		});
//});

//frappe.ui.form.on("Delivery Planning", "onload", function(frm) {
//        frm.call({
//				method : 'check_transporter_po_btn',
//				doc: frm.doc,
//				callback : function(r){
//					if (r.message)
//					{
//						if(r.message == 2){
//							if(frm.doc.docstatus === 1){
//							frm.set_df_property('show_purchase_order_planning_item','hidden',0)
//							frm.set_df_property('show_transporter_planning_item','hidden',0)
//							}
//						}
//
//						if(r.message == 2){
//							if(frm.doc.docstatus === 1){
//							frm.set_df_property('show_purchase_order_planning_item','hidden',1)
//							}
//						}
//						else if (r.message == 3){
//							if(frm.doc.docstatus === 1){
//							frm.set_df_property('show_transporter_planning_item','hidden',1)
//							}
//						}
//					}
//				}
//		});
//});
