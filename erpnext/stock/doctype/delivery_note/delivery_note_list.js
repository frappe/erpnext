frappe.listview_settings['Delivery Note'] = {
	add_fields: ["customer", "customer_name", "base_grand_total", "per_installed", "per_billed", 
		"transporter_name", "grand_total", "is_return", "status"],
	get_indicator: function(doc) {
		if(cint(doc.is_return)==1) {
			return [__("Return"), "darkgrey", "is_return,=,Yes"];
		} else if(doc.status==="Closed") {
			return [__("Closed"), "green", "status,=,Closed"];
		}  else if (flt(doc.per_billed, 2) < 100) {
			return [__("To Bill"), "orange", "per_billed,<,100"];
		} else if (flt(doc.per_billed, 2) == 100) {
			return [__("Completed"), "green", "per_billed,=,100"];
		}
	}
};
