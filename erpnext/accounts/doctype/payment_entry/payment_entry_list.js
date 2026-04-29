frappe.listview_settings["Payment Entry"] = {
	add_fields: ["unallocated_amount", "docstatus"],
	get_indicator: function (doc) {
		if (doc.docstatus === 2) {
			return [__("Cancelled"), "red", "docstatus,=,2"];
		}

		if (doc.docstatus === 0) {
			return [__("Draft"), "orange", "docstatus,=,0"];
		}

		if (flt(doc.unallocated_amount) > 0) {
			return [__("Unreconciled"), "orange", "docstatus,=,1|unallocated_amount,>,0"];
		}

		return [__("Reconciled"), "green", "docstatus,=,1|unallocated_amount,=,0"];
	},
	onload: function (listview) {
		if (listview.page.fields_dict.party_type) {
			listview.page.fields_dict.party_type.get_query = function () {
				return {
					filters: {
						name: ["in", Object.keys(frappe.boot.party_account_types)],
					},
				};
			};
		}
	},
};
