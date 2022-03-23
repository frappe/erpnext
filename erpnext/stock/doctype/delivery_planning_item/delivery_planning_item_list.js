frappe.listview_settings['Delivery Planning Item'] = {
	add_fields: ["transporter", "sales_order", "customer", "customer_name","postal_code", "item_code", "item_name",
					"planned_date", "ordered_qty", "weight_to_deliver"],
	filters: [["docstatus", "=", "Submitted"]],				
	hide_name_column: true,

	onload: function(listview) {

		
		// cur_list.sort_selector.sort_by = "name"
		
		// document.getElementByClassName("btn btn-action btn-default btn-xs").style.backgroundColor = "lightblue";
		// listview.page.add_action_item(__("Approve"), function() {
		// 	const selected_docs = listview.get_checked_items();
		// 	const docnames = listview.get_checked_items(true);

			
		// 	if (selected_docs.length > 0) {
		// 		for (let doc of selected_docs) {
		// 				console.log(doc.name)
		// 		};
		// 	}
           
		// 	frappe.call({

		// 		type: "POST",
		// 				method: "erpnext.stock.doctype.delivery_planning_item.delivery_planning_item.approve_function",
		// 					args: {
		// 						"source_names": docnames
		// 					},
		// 					callback: function (r) {
		// 						console.log(r.message)
		// 						if (!r.exc) {
		// 							frappe.model.sync(r.message);
		// 							console.log(r.message)
		// 							cur_list.refresh();
		// 						}
		// 					}
		// 	});
		// });

        // listview.page.add_action_item(__("Reject"), function() {
		// 	const selected_docs = listview.get_checked_items();
		// 	const docnames = listview.get_checked_items(true);

			
		// 	if (selected_docs.length > 0) {
		// 		for (let doc of selected_docs) {
		// 				console.log(doc.name)
		// 		};
		// 	}
           
		// 	frappe.call({
		
		// 		type: "POST",
		// 				method: "erpnext.stock.doctype.delivery_planning_item.delivery_planning_item.reject_function",
		// 					args: {
		// 						"source_names": docnames
		// 					},
		// 					callback: function (r) {
		// 						console.log(r.message)
		// 						if (!r.exc) {
		// 							frappe.model.sync(r.message);
		// 							console.log(r.message)
		// 							cur_list.refresh();
		// 						}
		// 					}
		// 	});
		// });

		// listview.page.add_action_item(__("Split"), function() {
		// 	const selected_docs = listview.get_checked_items();
		// 	const docnames = listview.get_checked_items(true);
		// 	var supplier_dc_check = 0;

			
		// 	if (selected_docs.length > 0) {
		// 		for (let doc of selected_docs) {
		// 				console.log(doc.name)
		// 		};
		// 	}
		// 		console.log(docnames)
		// 		console.log(selected_docs)
		// 		console.log(selected_docs[0].transporter)
		// 		console.log(selected_docs[0].supplier_dc)
		// 		console.log(selected_docs[0].supplier)
			
		// 		if (docnames.length > 1){
		// 			frappe.msgprint({
		// 				title: __('Notification'),
		// 				indicator: 'Red',
		// 				message: __('Please select only one item to split ')
		// 			});
		// 		}
		// 		else if(selected_docs[0].docstatus == 1){
		// 			frappe.msgprint({
		// 				title: __('Notification'),
		// 				indicator: 'Red',
						
		// 				message: __('Cannot split submitted document')
		// 			});
		// 		}
		// 		else if( selected_docs[0].qty_to_deliver <=1){
		// 			frappe.msgprint({
		// 				title: __('Notification'),
		// 				indicator: 'Red',
						
		// 				message: __('Cannot split item with qty = 1')
		// 			});
		// 		}
			
		// 		// if(docnames.length == 1 ){
		// 		else{
		// 		console.log("Inside splite if with item" , docnames)
		// 		var new_supplier;
		// 		var new_warehouse;
		// 		var new_transporter;
		// 		var new_date;
				
		// 		if(selected_docs[0].transporter == "" || selected_docs[0].transporter == null ){
		// 			supplier_dc_check = 1;
		// 			console.log("inside IF supplier dc",selected_docs[0].supplier)
		// 		}
		// 		else{supplier_dc_check = 0;}

		// 		let d = new frappe.ui.Dialog({
		// 			title: 'Split Planning Item',
		// 			fields: [
		// 				{
		// 					label: 'Transporter',
		// 					fieldname: 'transporter',
		// 					fieldtype: 'Link',
		// 					options: "Supplier",
		// 					onchange: function() {
		// 						frappe.model.get_value('Supplier', {"name":d.fields_dict.transporter.value}, 'supplier_name',
		// 						function(dd){								
		// 							if (d.fields_dict.transporter.value){
		// 								d.fields_dict.transporter_name.value = dd.supplier_name;
		// 								d.fields_dict.transporter_name.refresh();
		// 							}
		// 							else{
		// 								d.fields_dict.transporter_name.value = "Please select Transporter";
		// 								d.fields_dict.transporter_name.refresh();
		// 							}
		// 						})
		// 					},
		// 					depends_on: "eval: doc.supplier_dc == 0",
		// 					mandatory_depends_on : "eval: doc.supplier_dc == 0",
		// 				},
		// 				{
		// 					label: 'Transporter Name',
		// 					fieldname: 'transporter_name',
		// 					fieldtfieldtype: 'Data',
		// 					read_only: 1,
		// 					depends_on: "eval: doc.supplier_dc == 0",
		// 					mandatory_depends_on : "eval: doc.supplier_dc == 0",
		// 					default: "Please select Transporter",
		// 				},
		// 				{
		// 					label: 'Deliver Date',
		// 					fieldname: 'delivery_date',
		// 					fieldtype: 'Date',
		// 					reqd: 1
		// 				},
		// 				{
		// 					label: 'Qty To Deliver',
		// 					fieldname: 'qty',
		// 					fieldtype: 'Float',
		// 					default : 1,
		// 					reqd: 1
		// 				},
		// 				{
		// 					label: 'Source Warehouse',
		// 					fieldname: 'src_warehouse',
		// 					fieldtype: 'Link',
		// 					options: "Warehouse",
		// 					default: selected_docs[0].sorce_warehouse,
		
		// 				},
		// 				{
		// 					label: 'Supplier delivers to Customer ',
		// 					fieldname: 'supplier_dc',
		// 					default: supplier_dc_check,
		// 					fieldtype: 'Check'
		// 				},
		// 				{
		// 					label: 'Supplier',
		// 					fieldname: 'supplier',
		// 					fieldtype: 'Link',
		// 					options: "Supplier",
		// 					depends_on: "eval: doc.supplier_dc == 1 ",
		// 					mandatory_depends_on : "eval: doc.supplier_dc == 1",
		// 					onchange: function() {
		// 						frappe.model.get_value('Supplier', {"name":d.fields_dict.supplier.value}, 'supplier_name',
		// 						function(dd){		
		// 							if (d.fields_dict.supplier.value){						
		// 							d.fields_dict.supplier_name.value = dd.supplier_name
		// 							d.fields_dict.supplier_name.refresh();
		// 							}
		// 							else{
		// 								d.fields_dict.supplier_name.value = "Please select Supplier";
		// 								d.fields_dict.supplier_name.refresh();
		// 							}
		// 						})
		// 					},
		// 				},
		// 				{
		// 					label: 'Supplier Name',
		// 					fieldname: 'supplier_name',
		// 					fieldtype: 'Data',
		// 					ddepends_on: "eval: doc.supplier_dc == 1 ",
		// 					mandatory_depends_on : "eval: doc.supplier_dc == 1",
		// 					read_only: 1,
		// 					default: "Please select Supplier"
		// 				}
		// 			],
		
		// 			primary_action_label: 'Submit',
		// 			primary_action(values) {
		// 				console.log(values);
		// 				if(values.transporter)
		// 				{ new_transporter = values.transporter;
		// 					console.log("0000000110000000",new_transporter);
		// 				}
						
		// 				else{ new_transporter = "";
		// 					console.log("0000000011000000",new_transporter);
		// 				}
		// 				if(values.supplier)
		// 				{ new_supplier = values.supplier;
		// 					console.log("00000000000000",new_supplier);
		// 				}
						
		// 				else{ new_supplier = "";
		// 					console.log("00000000000000",new_supplier);
		// 				}
		
		// 				if(values.src_warehouse)
		// 				{ new_warehouse = values.src_warehouse;
		// 					console.log("0000000110000000",new_warehouse);
		// 				}
						
		// 				else{ new_warehouse = "";
		// 					console.log("0000000011000000",new_warehouse);
		// 				}
		
		// 				if(values.qty == 0 || values.qty >= selected_docs[0].qty_to_deliver)
		// 				{
		// 					frappe.msgprint({
		// 						title: __('Warning'),
		// 						indicator: 'red',
		// 						message: __('Qty To Deliver should be greater than 0 or  less than Item selected to split')
		// 						});
		// 						console.log("values.qty",values.qty,selected_docs[0].qty_to_deliver)
		// 				}
					
		// 				else {			
		// 					frappe.call({
		// 					method: "erpnext.stock.doctype.delivery_planning_item.delivery_planning_item.split_function",
		// 					type: "POST",
		// 					args: {
		// 							"source_names": docnames,
		// 							"n_transporter": new_transporter,
		// 							"n_qty" : values.qty,
		// 							"n_src_warehouse" : new_warehouse,
		// 							"n_supplier_dc" : values.supplier_dc,
		// 							"n_supplier" : new_supplier,
		// 							"n_date" : values.delivery_date
		// 						  },
		
		// 					callback: function(r){
		// 						if(r.message){
		// 							console.log("item",r);
		// 							frappe.msgprint({
		// 								title: __('Notification'),
		// 								indicator: 'green',
		// 								message: __('Document updated successfully')
		// 								});
		// 								d.hide();
		// 								// location.reload();
		// 								cur_list.refresh();
										
		// 								console.log("curent list", cur_list)	
		// 							}
		// 						else{
		// 							frappe.msgprint({
		// 							title: __('Notification'),
		// 							indicator: 'red',
		// 							message: __('Document update failed')
									
		// 							});
		// 							d.hide();
		// 							}
		// 						}
		// 					});
		// 				}		
		// 			}
		// 		});
		// 		d.show();
		// 	}			
		// });
	},

	gantt_custom_popup_html: function(ganttobj, delivery_planning_item) {
		var html = `<div class="details-container"><h5><a style="text-decoration:underline"\
			href="/app/delivery_planning_item/${ganttobj.id}""> ${ganttobj.name} </a></h5>`;
		html += `<p style="color:white">Sales Order: ${delivery_planning_item.sales_order}</p>`
		html += `<p style="color:white">Customer: ${delivery_planning_item.customer}</p>`
		html += `<p style="color:white">Weight to deliver: ${delivery_planning_item.weight_to_deliver}</p>`

		if(delivery_planning_item.transporter) 	
		html += `<p style="color:white">Transporter: ${delivery_planning_item.transporter_name}</p>`;
		else
		html += `<p style="color:white">Supplier: ${delivery_planning_item.supplier_name}</p>`;
		html +=`</div>`
		return html;
	},
	
	// btn btn-action btn-default btn-xs

	button: {
        show(doc) {
			return doc.name;
        },
        get_label() {
            return 'Split';
        },
        get_description(doc) {
            return __('View {0}', [`${doc.reference_type} ${doc.reference_name}`])
        },
        action(doc) {
			var new_supplier;
				var new_warehouse;
				var new_transporter;
				var new_date;
            // frappe.set_route('Delivery Planning Item', doc.reference_type, doc.reference_name);
			if(doc.docstatus == 1){
				
					frappe.msgprint({
					title: __('Notification'),
					indicator: 'red',
					message: __('Cannot Split Submitted Document')
					});
			}

			else if(doc.docstatus == 2){
				
				frappe.msgprint({
				title: __('Notification'),
				indicator: 'red',
				message: __('Cannot Split Cancelled Document')
				});
		}

			else if( doc.ordered_qty <=1){
				frappe.msgprint({
					title: __('Notification'),
					indicator: 'Red',
					message: __('Cannot split item with qty = 1')
				});
			}

			else if( doc.transporter == null && doc.supplier == null){
				frappe.msgprint({
					title: __('Notification'),
					indicator: 'Red',
					message: __('Cannot split Please add Transporter or Supplier')
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
						onchange: function() {
							frappe.model.get_value('Supplier', {"name":d.fields_dict.transporter.value}, 'supplier_name',
							function(dd){								
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
						depends_on: "eval: doc.supplier_dc == 0",
						mandatory_depends_on : "eval: doc.supplier_dc == 0",
						default: doc.transporter
					},
					{
						label: 'Transporter Name',
						fieldname: 'transporter_name',
						fieldtype: 'Data',
						depends_on: "eval: doc.supplier_dc == 0 ",
						mandatory_depends_on : "eval: doc.supplier_dc == 0",
						read_only: 1,
						default: doc.transporter_name
					},
					{
						label: 'Deliver Date',
						fieldname: 'delivery_date',
						fieldtype: 'Date',
						reqd: 1,
						default : doc.delivery_date	
					},
					{
						label: 'Current Qty To Deliver',
						fieldname: 'qty_td',
						fieldtype: 'Float',
						default : doc.qty_to_deliver,
						read_only: 1
					},
					{
						label: 'Current Pending Qty',
						fieldname: 'qty_pd',
						fieldtype: 'Float',
						default : doc.pending_qty,
						read_only: 1
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
						default: doc.sorce_warehouse,
	
					},
					{
						label: 'Batch',
						fieldname: 'batch_no',
						fieldtype: 'Link',
						options: "Batch",
						"get_query": function () {
							let filters = {
								'item_code': doc.item_code,
								'posting_date': doc.planned_date || frappe.datetime.nowdate(),
								'warehouse': doc.sorce_warehouse
							}
							return {
								query : "erpnext.controllers.queries.get_batch_no",
								filters: filters
							}
						}
					},
					{
						label: 'Supplier delivers to Customer ',
						fieldname: 'supplier_dc',
						default: 0,
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
					if(values.transporter)
					{ new_transporter = values.transporter;
					}
					
					else{ new_transporter = "";
					}
					if(values.supplier)
					{ new_supplier = values.supplier;
					}
					
					else{ new_supplier = "";
					}
	
					if(values.src_warehouse)
					{ new_warehouse = values.src_warehouse; 
					}
					
					else{ new_warehouse = ""; 
					}
	
					if(values.qty == 0 || values.qty >= doc.qty_to_deliver)
					{
						frappe.msgprint({
							title: __('Warning'),
							indicator: 'red',
							message: __('Qty To Deliver should be greater than 0 or  less than Item selected to split')
							});
					}
				
					else {			
						frappe.call({
						method: "erpnext.stock.doctype.delivery_planning_item.delivery_planning_item.split_function",
						type: "POST",
						args: {
								"source_names": doc.name,
								"n_transporter": new_transporter,
								"n_qty" : values.qty,
								"n_src_warehouse" : new_warehouse,
								"n_supplier_dc" : values.supplier_dc,
								"n_supplier" : new_supplier,
								"n_date" : values.delivery_date,
								"batch_no" : values.batch_no
						},
	
						callback: function(r){
							if(r.message){
								frappe.msgprint({
									title: __('Notification'),
									indicator: 'green',
									message: __('Document updated successfully')
									});
									d.hide();
									// location.reload();
									cur_list.refresh();
										
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
        }
    },

};
