frappe.listview_settings["Customer"] = {
	add_fields: ["customer_name", "territory", "customer_group", "customer_type", "image"],

	onload(listview) {
		listview.page.add_menu_item(__("Import Customers"), () => {
			frappe.set_route("party-import-wizard");
			// The wizard's step 1 prompts for party type; we could pre-pick Customer
			// by stashing state — wizard reads `frappe.party_import_prefill` on load.
			window.localStorage.setItem("party_import_prefill", "Customer");
		});
	},
};
