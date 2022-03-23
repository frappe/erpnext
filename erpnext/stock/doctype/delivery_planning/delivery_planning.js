// Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Delivery Planning', {

	on_submit: function(frm){
		frm.call({
			method:'on_delivery_planning_submit',
			doc: frm.doc,
			callback: function(r){
				if(r.message){
					console.log('Submitted')
				}
				frm.reload_doc();
			}	
		});
	},

	before_save: function(frm){
		if(frm.doc.delivery_date_from > frm.doc.delivery_date_to)
		{ frappe.throw(__('Delivery Date To should be greater or equal to Date From '))}
	},
	onload: function(frm){
		var prev_route = frappe.get_prev_route();
		if (prev_route[1] == "Delivery Planning Item"){

				location.reload();
		}

		// status refresh
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

		if( frm.doc.docstatus === 1 ){

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

		// code for button visibility on certian condition
		frm.call({
				method : 'check_transporter_po_btn',
				doc: frm.doc,
				callback : function(r){
						if(r.message == 1){
							console.log(r.message)
							}

						else if(r.message == 2){
							frm.set_df_property('show_purchase_order_planning_item','hidden',1)
							frm.refresh_field('show_purchase_order_planning_item')
						}
						else if (r.message == 3){
							frm.set_df_property('show_transporter_planning_item','hidden',1)
							frm.refresh_field('show_transporter_planning_item')

						}
						else{
							frm.set_df_property('show_purchase_order_planning_item','hidden',1)
							frm.set_df_property('show_transporter_planning_item','hidden',1)
							frm.refresh_field('show_purchase_order_planning_item')
							frm.refresh_field('show_transporter_planning_item')
						}
					}
				});

//	 	code for create and calcluate custom button

		frm.call({
				method : 'check_po_in_dpi',
				doc: frm.doc,
				callback : function(r){
					if(r.message == 1){

							//  custom button to populate Transporter wise Delivery Planning
							frm.add_custom_button(__("Transporter Planning Item Summary"), function() {

								frm.call({
									method : 'summary_call',
									doc: frm.doc,
									callback : function(r){
										if(r.message == 1){											
											// frm.refresh();
											location.reload();
											frappe.msgprint("  Transporter wise Delivery Plan created");
										}
										else{
										frappe.msgprint(" Unable to create Transporter wise Delivery Plan   ");
										}
								   	}
								});
							
								frm.call({
									method:'refresh_status',
									doc: frm.doc,
									callback: function(r){
										if(r.message){
											frm.refresh_field('d_status')
										}
									}
										
								});	
								
							},__("Calculate"));

							//custom button to generate Purchase Order Planning Items
							frm.add_custom_button(__("Purchase Order Planning Item Summary"), function() {
							frm.call({
								method : 'purchase_order_call',
								doc: frm.doc,

								callback : function(r){
									if(r.message == 1){
											frappe.msgprint(" Purchase Order Plan Items created  ");
											location.reload();
										}
									else{
										frappe.msgprint(" Unable to create Purchase Delivery Plan Item   ");
										}
							   }
							});
								frm.call({
									method:'refresh_status',
									doc: frm.doc,
									callback: function(r){
										if(r.message){
											frm.refresh_field('d_status')
										}
									}
								});
							},__("Calculate"));

						// custom button Create for Purchase Order Creation
							frm.add_custom_button(__('Purchase Order '), function () {
								frm.call({
									method : 'make_po',
									doc: frm.doc,
									callback : function(r){
										if(r.message == 1){
											// frm.refresh();
											frappe.msgprint("  Purchase Order created ");
											frm.reload_doc();
										}
										else{
											frappe.msgprint(" Purchase Order already created ");
										}
								   }
								});
								frm.call({
									method:'refresh_status',
									doc: frm.doc,
									callback: function(r){
										if(r.message){
											frm.refresh_field('d_status')
										}
									}		
								});
							}, __('Create'));

							//custom button 'Create' for Pick List
							frm.add_custom_button(__('Pick List'), function () {
								frm.call({
									method : 'make_picklist',
									doc: frm.doc,
									callback : function(r){
										if(r.message == 1){
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
											frappe.msgprint({
											title: __('Delivery Note created'),
											message: __('Created Delivery note using Pick List'),
											indicator: 'green'
										});
										frm.reload_doc();
										}
										else if(r.message == 2){
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
										
								   }
								});
							}, __('Create'));
					}
					else if(r.message == 2){
							//custom button to generate Purchase Order Planning Items
							
							frm.add_custom_button(__("Purchase Order Planning Item Summary"), function() {
								frm.call({
									method : 'purchase_order_call',
									doc: frm.doc,

									callback : function(r){
										if(r.message == 1){
												// frm.refresh();
												frappe.msgprint(" Purchase Order Plan Items created  ");
												location.reload();
											}
										else{
											frappe.msgprint(" Unable to create Purchase Delivery Plan Item   ");
											}
								}
								});
								frm.call({
									method:'refresh_status',
									doc: frm.doc,
									callback: function(r){
										if(r.message){
											frm.refresh_field('d_status')
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
											frappe.msgprint("  Purchase Order created ");
											location.reload();
										}
										else{
											frappe.msgprint(" Purchase Order already created ");
										}
								   }
								});
								frm.reload_doc();
							}, __('Create'));
						}

					else if(r.message == 3 ){
						console.log(r.message);

//							Transporter Summary inside Calcluate button
							frm.add_custom_button(__("Transporter Planning Item Summary"), function() {

								frm.call({
									method : 'summary_call',
									doc: frm.doc,
									callback : function(r){
										if(r.message == 1){
											frappe.msgprint("  Transporter wise Delivery Plan created  ");
											location.reload();
											// frm.reload_doc();
											
										}
										else{
										frappe.msgprint(" Unable to create Transporter wise Delivery Plan   ");
										}
										frm.reload_doc();
								   }
								});
							},__("Calculate"));

							//custom button 'Create' for Pick List
							frm.add_custom_button(__('Pick List'), function () {
								frm.call({
									method : 'make_picklist',
									doc: frm.doc,
									callback : function(r){
										if(r.message == 1){
											frm.reload_doc();
											frappe.msgprint(" Pick List created ");
										
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
											frappe.msgprint({
											title: __('Delivery Note created'),
											message: __('Created Delivery note using Pick List'),
											indicator: 'green'
										});
										frm.reload_doc();
										}
										else if(r.message == 2){
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
											message: __('Delivery Note already created'),
											indicator: 'orange'
										});
										}
								   }
								});
								frm.call({
									method:'refresh_status',
									doc: frm.doc,
									callback: function(r){
										if(r.message){
											frm.refresh_field('d_status')
										}
									}				
								});

							}, __('Create'));
					}
					else{
						console.log(r.message);
					}
			   }
		});
		}
    },


	refresh: function(frm) {

		var prev_route = frappe.get_prev_route();
		if (prev_route[1] == "Delivery Planning Item"){

				location.reload();
		}
		
		if (frm.doc.docstatus == 1 && frm.doc.d_status != "Pending Planning"){
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
