frappe.listview_settings['Delivery Planning Item'] = {
	add_fields: ["transporter", "sales_order", "customer", "customer_name","postal_code", "item_code", "item_name",
					"delivery_date", "ordered_qty", "approved", "weight_to_deliver"],
	hide_name_column: true,
	onload: function(listview) {

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
									cur_frm.dirty();
									cur_frm.refresh();
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
									cur_frm.dirty();
									cur_frm.refresh();
								}
							}
			});
		});

		listview.page.add_action_item(__("Split"), function() {
			const selected_docs = listview.get_checked_items();
			const docnames = listview.get_checked_items(true);

			
			if (selected_docs.length > 0) {
				for (let doc of selected_docs) {
						console.log(doc.name)
				};
			}
				// console.log(selected)
			if(docnames == 1){
				frappe.call({
					// method:'erpnext.stock.doctype.delivery_planning_item.delivery_planning_item.approve_function',
					// args: { selected_docs : selected_docs,
					// selected_docs: selected_docs },
					// callback: function(r) {
					// 	listview.refresh();
					// }

					type: "POST",
							method: "erpnext.stock.doctype.delivery_planning_item.delivery_planning_item.split_function",
								args: {
									"source_names": docnames
								},
								callback: function (r) {
									console.log(r.message)
									if (!r.exc) {
										frappe.model.sync(r.message);
										console.log(r.message)
										cur_frm.dirty();
										cur_frm.refresh();
									}
								}
				});
			}
			else{
				frappe.msgprint({
					title: __('Notification'),
					indicator: 'Red',
					message: __('Please select only one item to split')
				});
			}
		});

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