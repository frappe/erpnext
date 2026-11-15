frappe.listview_settings["Payment Entry"] = {
	add_fields: ["unallocated_amount", "party_type"],
	get_indicator: function (doc) {
		if (
			doc.docstatus == 1 &&
			flt(doc.unallocated_amount) > 0 &&
			["Customer", "Supplier"].includes(doc.party_type)
		) {
			return [__("Unallocated"), "orange", "docstatus,=,1|unallocated_amount,>,0"];
		}
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
