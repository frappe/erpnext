frappe.listview_settings['Sales Order'] = {
	add_fields: ["base_grand_total", "customer_name", "currency", "delivery_date", "per_delivered", "per_billed",
		"status"],
	get_indicator: function(doc) {
        if(doc.status==="Stopped") {
			return [__("Stopped"), "darkgrey", "status,=,Stopped"];
        } else if(flt(doc.per_delivered) < 100 && frappe.datetime.get_diff(doc.delivery_date) < 0) {
			return [__("Overdue"), "red", "per_delivered,<,100|delivery_date,<,Today|status,!=,Stopped"];
		} else if(flt(doc.per_delivered) < 100 && doc.status!=="Stopped") {
			return [__("Not Delivered"), "orange", "per_delivered,<,100|status,!=,Stopped"];
		} else if(flt(doc.per_delivered) == 100 && flt(doc.per_billed) < 100 && doc.status!=="Stopped") {
			return [__("To Bill"), "orange", "per_delivered,=,100|per_billed,<,100|status,!=,Stopped"];
		} else if(flt(doc.per_delivered) == 100 && flt(doc.per_billed) == 100 && doc.status!=="Stopped") {
			return [__("Completed"), "green", "per_delivered,=,100|per_billed,=,100|status,!=,Stopped"];
		}
	},
	onload: function(listview) {
		var method = "erpnext.selling.doctype.sales_order.sales_order.stop_or_unstop_sales_orders";

		listview.page.add_menu_item(__("Set as Stopped"), function() {
			listview.call_for_selected_items(method, {"status": "Stop"});
		});

		listview.page.add_menu_item(__("Set as Unstopped"), function() {
			listview.call_for_selected_items(method, {"status": "Unstop"});
		});

	}
};
