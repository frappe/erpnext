frappe.listview_settings['Project'] = {
	add_fields: ["project_status", "status", "indicator_color", "priority", "is_active", "percent_complete", "project_name"],
	get_indicator: function(doc) {
		var percentage = "";
		if (doc.percent_complete && doc.status != "Completed") {
			percentage = " " + __("({0}%)", [cint(doc.percent_complete)]);
		}

		var color_map = {
			"Open": "orange",
			"Completed": "green",
			"Closed": "green",
			"Cancelled": "light-grey",
		}

		var guessed_color = color_map[doc.status] || frappe.utils.guess_colour(doc.status);

		if (doc.project_status) {
			return [
				__(doc.project_status) + percentage,
				doc.indicator_color || guessed_color,
				"project_status,=," + doc.project_status
			];
		} else {
			return [
				__(doc.status) + percentage,
				guessed_color,
				"status,=," + doc.status
			];
		}
	},

	onload: function(listview) {
		if (listview.page.fields_dict.customer) {
			listview.page.fields_dict.customer.get_query = () => {
				return erpnext.queries.customer();
			}
		}
		if (listview.page.fields_dict.bill_to) {
			listview.page.fields_dict.bill_to.get_query = () => {
				return erpnext.queries.customer();
			}
		}

		if (listview.page.fields_dict.applies_to_variant_of) {
			listview.page.fields_dict.applies_to_variant_of.get_query = () => {
				return erpnext.queries.item({"is_vehicle": 1, "has_variants": 1, "include_disabled": 1});
			}
		}

		if (listview.page.fields_dict.applies_to_item) {
			listview.page.fields_dict.applies_to_item.get_query = () => {
				var filters = {"include_disabled": 1};

				var variant_of;
				if (listview.page.fields_dict.applies_to_variant_of) {
					variant_of = listview.page.fields_dict.applies_to_variant_of.get_value('applies_to_variant_of')
				}
				if (variant_of) {
					filters['variant_of'] = variant_of;
				}

				return erpnext.queries.item(filters);
			}
		}
	}
};
