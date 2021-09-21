frappe.listview_settings['Vehicle Invoice Receipt'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		var indicator;

		if(doc.status === "Delivered") {
			indicator = [__(doc.status), "green", `status,=,${doc.status}`];
		} else if(doc.status === "In Hand") {
			indicator = [__(doc.status), "blue", `status,=,${doc.status}`];
		}

		return indicator;
	},
	onload: function(listview) {
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
