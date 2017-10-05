frappe.listview_settings['Opportunity'] = {
	add_fields: ["customer_name", "enquiry_type", "enquiry_from", "status"],
	get_indicator: function(doc) {
		let colour = doc.status == "Quotation"? "green":
			erpnext.utils.guess_colour_from_status(doc.status)
		return [__(doc.status), colour, "status,=," + doc.status];
	},
	onload: function(listview) {
		var method = "erpnext.crm.doctype.opportunity.opportunity.set_multiple_status";

		listview.page.add_menu_item(__("Set as Unreplied"), function() {
			listview.call_for_selected_items(method, {"status": "Unreplied"});
		});

		listview.page.add_menu_item(__("Set as Closed"), function() {
			listview.call_for_selected_items(method, {"status": "Closed"});
		});
	}
};
