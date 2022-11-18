frappe.listview_settings['Vehicle Delivery'] = {
	add_fields: ["is_return"],
	get_indicator: function(doc) {
		if(cint(doc.is_return)) {
			return [__("Returned"), "grey", "is_return,=,1"];
		} else {
			return [__("Delivered"), "green", "is_return,=,0"];
		}
	},
	onload: function(listview) {
		listview.page.fields_dict.customer.get_query = () => {
			return erpnext.queries.customer();
		}

		listview.page.fields_dict.variant_of.get_query = () => {
			return erpnext.queries.item({"is_vehicle": 1, "has_variants": 1, "include_disabled": 1});
		}

		listview.page.fields_dict.item_code.get_query = () => {
			var variant_of = listview.page.fields_dict.variant_of.get_value('variant_of');
			var filters = {"is_vehicle": 1, "include_disabled": 1};
			if (variant_of) {
				filters['variant_of'] = variant_of;
			}
			return erpnext.queries.item(filters);
		}
	}
};
