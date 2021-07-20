frappe.listview_settings['Delivery Planning Item'] = {
    onload: function(listview) {
		listview.page.add_action_item(__("Approve"), function() {
            console.log(" ----------- checked items",event.view.cur_list.$checks)
			frappe.call({
				method:'approve_function',
                doc: frm.doc,
				callback: function() {
					listview.refresh();
				}
			});
		});

        listview.page.add_action_item(__("Reject"), function() {
            console.log(" ------retectr----- checked items",event.view.cur_list.$checks)
            let selected = [];
                        for (let check of event.view.cur_list.$checks) {
                            selected.push(check.dataset.name);
                        }
			frappe.call({
				method:'reject_function',
                doc: frm.doc,
				callback: function() {
					listview.refresh();
				}
			});
		});

        listview.page.add_action_item(__("Split"), function() {
            console.log(" -----split------ checked items",event.view.cur_list.$checks)
            let selected = [];
                        for (let check of event.view.cur_list.$checks) {
                            selected.push(check.dataset.name);
                        }
                        console.log(" -----split------ checked items",selected)            
			frappe.call({
				method:'split_function',
                doc: frm.doc,
				callback: function() {
					listview.refresh();
				}
			});
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