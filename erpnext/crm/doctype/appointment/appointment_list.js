frappe.listview_settings['Appointment'] = {
	add_fields: ["status", "docstatus"],
	get_indicator: function (doc) {
		if (doc.docstatus == 2) {
			return [__(doc.status), "darkgrey", "docstatus,=," + doc.docstatus];
		} else if (doc.status == "Cancelled") {
			return [__(doc.status), "darkgrey", "status,=," + doc.status];
		} else if (doc.status == "Open") {
			return [__(doc.status), "orange", "status,=," + doc.status];
		} else if (doc.status == "Rescheduled") {
			return [__(doc.status), "blue", "status,=," + doc.status];
		} else if (doc.status == "Closed") {
			return [__(doc.status), "green", "status,=," + doc.status];
		}
	},

	has_indicator_for_cancelled: 1,

	onload: function(listview) {
		if (listview.page.fields_dict.appointment_for) {
			listview.page.fields_dict.appointment_for.get_query = function() {
				return {
					"filters": {
						"name": ["in", ["Customer", "Lead"]],
					}
				};
			};
		}

		if (listview.page.fields_dict.applies_to_variant_of) {
			listview.page.fields_dict.applies_to_variant_of.get_query = () => {
				return erpnext.queries.item({"has_variants": 1, "include_disabled": 1});
			}
		}

		if (listview.page.fields_dict.applies_to_item) {
			listview.page.fields_dict.applies_to_item.get_query = () => {
				var variant_of = listview.page.fields_dict.applies_to_variant_of.get_value('applies_to_variant_of');
				var filters = {"include_disabled": 1};
				if (variant_of) {
					filters['variant_of'] = variant_of;
				}
				return erpnext.queries.item(filters);
			}
		}
	},
}
