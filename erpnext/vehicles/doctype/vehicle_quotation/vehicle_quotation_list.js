frappe.listview_settings['Vehicle Quotation'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		if(doc.status==="Open") {
			return [__("Open"), "orange", "status,=,Open"];
		} else if(doc.status==="Ordered") {
			return [__("Ordered"), "green", "status,=,Ordered"];
		} else if(doc.status==="Lost") {
			return [__("Lost"), "grey", "status,=,Lost"];
		} else if(doc.status==="Expired") {
			return [__("Expired"), "light-grey", "status,=,Expired"];
		}
	},
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

		listview.page.fields_dict.party_name.get_query = () => {
			var quotation_to = listview.page.fields_dict.quotation_to.get_value('quotation_to');
			if (quotation_to == "Customer") {
				return erpnext.queries.customer();
			} else if (quotation_to == "Lead") {
				return erpnext.queries.lead();
			}
		}

		listview.page.fields_dict.variant_of.get_query = () => {
			return erpnext.queries.item({"is_vehicle": 1, "has_variants": 1, "include_disabled": 1, "include_in_vehicle_booking": 1});
		}

		listview.page.fields_dict.item_code.get_query = () => {
			var variant_of = listview.page.fields_dict.variant_of.get_value('variant_of');
			var filters = {"is_vehicle": 1, "include_disabled": 1, "include_in_vehicle_booking": 1};
			if (variant_of) {
				filters['variant_of'] = variant_of;
			}
			return erpnext.queries.item(filters);
		}
	}
};
