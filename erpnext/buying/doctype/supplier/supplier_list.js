frappe.listview_settings["Supplier"] = {
	add_fields: ["supplier_name", "supplier_group", "image", "on_hold"],
	get_indicator: function (doc) {
		if (cint(doc.on_hold)) {
			return [__("On Hold"), "red"];
		}
	},

	onload(listview) {
		listview.page.add_menu_item(__("Import Suppliers"), () => {
			window.localStorage.setItem("party_import_prefill", "Supplier");
			frappe.set_route("party-import-wizard");
		});
	},
};
