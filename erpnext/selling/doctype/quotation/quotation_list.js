frappe.listview_settings['Quotation'] = {
	add_fields: ["customer_name", "base_grand_total", "status",
		"company", "currency", 'valid_till'],

	onload: function(listview) {
		if (listview.page.fields_dict.quotation_to) {
			listview.page.fields_dict.quotation_to.get_query = function() {
				return {
					"filters": {
						"name": ["in", ["Customer", "Lead"]],
					}
				};
			};
		}
	},

	get_indicator: function(doc) {
		if(doc.status==="Open") {
			return [__("Open"), "orange", "status,=,Open"];
		} else if (doc.status==="Partially Ordered") {
			return [__("Partially Ordered"), "yellow", "status,=,Partially Ordered"];
		} else if(doc.status==="Ordered") {
			return [__("Ordered"), "green", "status,=,Ordered"];
		} else if(doc.status==="Lost") {
			return [__("Lost"), "gray", "status,=,Lost"];
		} else if(doc.status==="Expired") {
			return [__("Expired"), "gray", "status,=,Expired"];
		}
	}
};
