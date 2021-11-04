frappe.listview_settings['Vehicle Registration Order'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		var indicator;

		if(doc.status === "Completed") {
			indicator = [__("Completed"), "green", "status,=,Completed"];
		} else if(["To Pay Agent", "To Retrieve Invoice"].includes(doc.status)) {
			indicator = [__(doc.status), "purple", `status,=,${doc.status}`];
		} else if (["To Receive Payment", "To Receive Invoice", "To Receive Receipt"].includes(doc.status)) {
			indicator = [__(doc.status), "yellow", `status,=,${doc.status}`];
		} else if(["To Pay Authority", "To Issue Invoice", "To Deliver Invoice", "To Close Accounts"].includes(doc.status)) {
			indicator = [__(doc.status), "orange", `status,=,${doc.status}`];
		}

		return indicator;
	},
	onload: function(listview) {
		listview.page.fields_dict.customer.get_query = () => {
			return erpnext.queries.customer();
		}
		listview.page.fields_dict.registration_customer.get_query = () => {
			return erpnext.queries.customer();
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

		listview.page.add_action_item(__("Create Agent Payment"), function () {
			var names = listview.get_checked_items(true);

			if (names && names.length) {
				return frappe.call({
					method: "erpnext.vehicles.doctype.vehicle_registration_order.vehicle_registration_order.get_agent_payment_voucher",
					args: {
						"names": names
					},
					callback: function (r) {
						var doclist = frappe.model.sync(r.message);
						frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
					}
				});
			}
		});
	}
};
