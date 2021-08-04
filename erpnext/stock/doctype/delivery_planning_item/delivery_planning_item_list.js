frappe.listview_settings['Delivery Planning Item'] = {
	add_fields: ["transporter", "sales_order", "customer", "customer_name","postal_code", "item_code", "item_name",
					"delivery_date", "ordered_qty", "approved", "weight_to_deliver"],
	hide_name_column: true,
	onload: function(listview) {
		// cur_list.sort_selector.sort_by = "name"
		// cur_list.page_length = 1000

		listview.page.add_action_item(__("Approve"), function() {
			const selected_docs = listview.get_checked_items();
			const docnames = listview.get_checked_items(true);

			
			if (selected_docs.length > 0) {
				for (let doc of selected_docs) {
						console.log(doc.name)
				};
			}
				// console.log(selected)
           
			frappe.call({
				// method:'erpnext.stock.doctype.delivery_planning_item.delivery_planning_item.approve_function',
                // args: { selected_docs : selected_docs,
				// selected_docs: selected_docs },
				// callback: function(r) {
				// 	listview.refresh();
				// }

				type: "POST",
						method: "erpnext.stock.doctype.delivery_planning_item.delivery_planning_item.approve_function",
							args: {
								"source_names": docnames
							},
							callback: function (r) {
								console.log(r.message)
								if (!r.exc) {
									frappe.model.sync(r.message);
									console.log(r.message)
									cur_list.refresh();
								}
							}
			});
		});

        listview.page.add_action_item(__("Reject"), function() {
			const selected_docs = listview.get_checked_items();
			const docnames = listview.get_checked_items(true);

			
			if (selected_docs.length > 0) {
				for (let doc of selected_docs) {
						console.log(doc.name)
				};
			}
				// console.log(selected)
           
			frappe.call({
				// method:'erpnext.stock.doctype.delivery_planning_item.delivery_planning_item.approve_function',
                // args: { selected_docs : selected_docs,
				// selected_docs: selected_docs },
				// callback: function(r) {
				// 	listview.refresh();
				// }

				type: "POST",
						method: "erpnext.stock.doctype.delivery_planning_item.delivery_planning_item.reject_function",
							args: {
								"source_names": docnames
							},
							callback: function (r) {
								console.log(r.message)
								if (!r.exc) {
									frappe.model.sync(r.message);
									console.log(r.message)
									cur_list.refresh();
								}
							}
			});
		});

		listview.page.add_action_item(__("Split"), function() {
			const selected_docs = listview.get_checked_items();
			const docnames = listview.get_checked_items(true);
			var supplier_dc_check = 0;

			
			if (selected_docs.length > 0) {
				for (let doc of selected_docs) {
						console.log(doc.name)
				};
			}
				console.log(docnames)
				console.log(selected_docs)
				console.log(selected_docs[0].transporter)
				console.log(selected_docs[0].supplier_dc)
				console.log(selected_docs[0].supplier)
			
				if (docnames.length > 1){
					frappe.msgprint({
						title: __('Notification'),
						indicator: 'Red',
						message: __('Please select only one item to split ')
					});
				}
				else if( selected_docs[0].qty_to_deliver <=1){
					frappe.msgprint({
						title: __('Notification'),
						indicator: 'Red',
						
						message: __('Select item with delivery qty greater than 1')
					});
				}
			
				// if(docnames.length == 1 ){
				else{
				console.log("Inside splite if with item" , docnames)
				var new_supplier;
				var new_warehouse;
				var new_transporter;
				var new_date;

				

				if(selected_docs[0].transporter == "" || selected_docs[0].transporter == null ){
					supplier_dc_check = 1;
					console.log("inside IF supplier dc",selected_docs[0].supplier)
				}
				else{supplier_dc_check = 0;}

				let d = new frappe.ui.Dialog({
					title: 'Split Planning Item',
					fields: [
						{
							label: 'Transporter',
							fieldname: 'transporter',
							fieldtype: 'Link',
							options: "Supplier",
							default: selected_docs[0].transporter,
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
							default: selected_docs[0].sorce_warehouse,
		
						},
						{
							label: 'Supplier delivers to Customer ',
							fieldname: 'supplier_dc',
							default: supplier_dc_check,
							fieldtype: 'Check'
						},
						{
							label: 'Supplier',
							fieldname: 'supplier',
							fieldtype: 'Link',
							options: "Supplier",
							default: selected_docs[0].supplier,
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
		
						if(values.qty == 0 || values.qty >= selected_docs[0].qty_to_deliver)
						{
							frappe.msgprint({
								title: __('Warning'),
								indicator: 'red',
								message: __('Qty To Deliver should be greater than 0 or  less than Item selected to split')
								});
							
							// frappe.throw(__('Qty to delivery should be geater than 0 and less than {0}').format(self.qty_to_deliver))
							console.log("values.qty",values.qty,selected_docs[0].qty_to_deliver)
						}
					
						else {			
							frappe.call({
							// doc:selected_docs[0],
							method: "erpnext.stock.doctype.delivery_planning_item.delivery_planning_item.split_function",
							type: "POST",
							// 			method: "erpnext.stock.doctype.delivery_planning_item.delivery_planning_item.split_function",
							// 				args: {
							// 					"source_names": docnames
							// 				},
							args: {
									"source_names": docnames,
									"n_transporter": new_transporter,
									"n_qty" : values.qty,
									"n_src_warehouse" : new_warehouse,
									"n_supplier_dc" : values.supplier_dc,
									"n_supplier" : new_supplier,
									"n_date" : values.delivery_date
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
										// location.reload();
										cur_list.refresh();
										
										console.log("curent list", cur_list)
										// frappe.set_route("Report", "Delivery Planning Item");
										// frappe.route_options = {"related_delivery_planning": frm.doc.related_delivey_planning };
										// frappe.set_route("List","Delivery Planning Item", {
										// 	"related_delivey_planning": frm.doc.related_delivey_planning
										// });
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


				// frappe.call({
				// 	// method:'erpnext.stock.doctype.delivery_planning_item.delivery_planning_item.approve_function',
				// 	// args: { selected_docs : selected_docs,
				// 	// selected_docs: selected_docs },
				// 	// callback: function(r) {
				// 	// 	listview.refresh();
				// 	// }

				// 	type: "POST",
				// 			method: "erpnext.stock.doctype.delivery_planning_item.delivery_planning_item.split_function",
				// 				args: {
				// 					"source_names": docnames
				// 				},
				// 				callback: function (r) {
				// 					console.log(r.message)
				// 					if (!r.exc) {
				// 						frappe.model.sync(r.message);
				// 						console.log(r.message)
				// 						cur_frm.dirty();
				// 						cur_frm.refresh();
				// 					}
				// 				}
				// });
			}
			
		});

	},
	gantt_custom_popup_html: function(ganttobj, task) {
		var html = `<h5><a style="text-decoration:underline"\
			href="/app/task/${ganttobj.id}""> ${ganttobj.name} </a></h5>`;

		if(task.project) html += `<p>Project: ${task.project}</p>`;
		html += `<p>Progress: ${ganttobj.progress}</p>`;

		if(task._assign_list) {
			html += task._assign_list.reduce(
				(html, user) => html + frappe.avatar(user)
			, '');
		}

		return html;
	}

};

// $(document).bind('DOMSubtreeModified', function () {
//     if ('List/Sales Invoice/List' in frappe.pages && frappe.pages['List/Sales Invoice/List'].page && !added) {
//         added = true;
//         frappe.pages['List/Sales Invoice/List'].page.add_action_item('Export to Quickbooks', function(event) {
//             // Convert list of UI checks to list of IDs
//             let selected = [];
//             for (let check of event.view.cur_list.$checks) {
//                 selected.push(check.dataset.name);
//             }
//             // Do action
//         });
        
//     }
// });