frappe.listview_settings["Party Import Log"] = {
	add_fields: ["status", "party_type", "total_rows", "imported_rows"],

	get_indicator(doc) {
		const map = {
			Draft: ["Draft", "grey", "status,=,Draft"],
			Mapping: ["Mapping", "blue", "status,=,Mapping"],
			Resolving: ["Resolving", "blue", "status,=,Resolving"],
			Reviewing: ["Reviewing", "blue", "status,=,Reviewing"],
			Importing: ["Importing", "orange", "status,=,Importing"],
			Completed: ["Completed", "green", "status,=,Completed"],
			Failed: ["Failed", "red", "status,=,Failed"],
			Cancelled: ["Cancelled", "grey", "status,=,Cancelled"],
		};
		return map[doc.status];
	},

	onload(listview) {
		listview.page.set_primary_action(
			__("New Import"),
			() => {
				frappe.set_route("party-import-wizard");
			},
			"add"
		);
	},
};
