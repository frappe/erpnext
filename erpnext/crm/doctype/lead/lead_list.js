frappe.listview_settings['Lead'] = {
	onload: function(listview) {
		if (frappe.boot.user.can_create.includes("Prospect")) {
			listview.page.add_action_item(__("Create Prospect"), function() {
				let leads = listview.get_checked_items();
				console.log(listview.get_checked_items());
				frappe.model.open_mapped_doc({
					method: "erpnext.crm.doctype.lead.lead.make_prospect",
					frm: cur_frm,
					leads: leads
				})

				// listview.call_for_selected_items(method, {"status": "Open"});
			// 	let prospect_lead = []
			// 	leads.forEach(lead => {
			// 		prospect_lead.push({
			// 			"lead": lead.name
			// 		});
			// 	});
			// 	console.log("check");
			// 	console.log(prospect_lead);
			// 	frappe.new_doc("Prospect", {
			// 		"company_name": leads[0].company_name,
			// 		"industry": leads[0].industry,
			// 		"market_segment": leads[0].market_segment,
			// 		"territory": leads[0].territory,
			// 		"no_of_employees": leads[0].no_of_employees,
			// 		"fax": leads[0].fax,
			// 		"website": leads[0].website,
			// 		"prospect_owner": leads[0].lead_owner,
			// 		"prospect_lead": prospect_lead
			// 	});
			});
		}
	}
};
