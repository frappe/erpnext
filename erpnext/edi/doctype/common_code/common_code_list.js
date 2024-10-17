frappe.listview_settings["Common Code"] = {
	onload: function (listview) {
		listview.page.add_inner_button(
			__("Genericode"),
			function () {
				erpnext.edi.import_genericode(listview);
			},
			__("Import")
		);
	},
	hide_name_column: true,
};
