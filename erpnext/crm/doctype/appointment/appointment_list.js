frappe.listview_settings['Appointment'] = {
	add_fields: ["status", "docstatus", "end_dt"],
	get_indicator: function (doc) {
		if (doc.status == "Open") {
			var is_late = false;
			if (doc.end_dt) {
				var now_dt = moment(frappe.datetime.now_datetime(true));
				var end_dt = frappe.datetime.str_to_obj(doc.end_dt);

				if (now_dt.isAfter(end_dt)) {
					is_late = true;
				}
			}

			if (is_late) {
				return [__("Late"), "yellow", "status,=," + doc.status];
			} else {
				return [__(doc.status), "orange", "status,=," + doc.status];
			}
		} else if (doc.status == "Rescheduled") {
			 return [__(doc.status), "light-blue", "status,=," + doc.status];
		} else if (doc.status == "Missed") {
			return [__(doc.status), "grey", "status,=," + doc.status];
		} else if (doc.status == "Closed") {
			return [__(doc.status), "green", "status,=," + doc.status];
		}
	},

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
