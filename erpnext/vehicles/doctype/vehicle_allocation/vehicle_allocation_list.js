frappe.listview_settings['Vehicle Allocation'] = {
	add_fields: ["is_booked"],
	get_indicator: function (doc) {
		if (doc.is_booked) {
			return [__("Booked"), "green", "is_booked,=,1"];
		} else {
			return [__("Available"), "blue", "is_booked,=,0"];
		}
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
