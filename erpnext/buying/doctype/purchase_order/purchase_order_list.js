frappe.listview_settings['Purchase Order'] = {
	add_fields: ["base_grand_total", "company", "currency", "supplier",
		"supplier_name", "per_received", "per_billed", "status"],
	get_indicator: function(doc) {
        if(doc.status==="Stopped") {
			return [__("Stopped"), "darkgrey", "status,=,Stopped"];
		} else if(flt(doc.per_received) < 100 && doc.status!=="Stopped") {
			return [__("Not Received"), "orange", "per_received,<,100|status,!=,Stopped"];
		} else if(flt(doc.per_received) == 100 && flt(doc.per_billed) < 100 && doc.status!=="Stopped") {
			return [__("To Bill"), "orange", "per_received,=,100|per_billed,<,100|status,!=,Stopped"];
		} else if(flt(doc.per_received) == 100 && flt(doc.per_billed) == 100 && doc.status!=="Stopped") {
			return [__("Completed"), "green", "per_received,=,100|per_billed,=,100|status,!=,Stopped"];
		}
	},
	onload: function(listview) {
		var method = "erpnext.buying.doctype.purchase_order.purchase_order.stop_or_unstop_purchase_orders";

		listview.page.add_menu_item(__("Set as Stopped"), function() {
			listview.call_for_selected_items(method, {"status": "Stopped"});
		});

		listview.page.add_menu_item(__("Set as Unstopped"), function() {
			listview.call_for_selected_items(method, {"status": "Submitted"});
		});

	}
};
