frappe.listview_settings["Employee"] = {
	add_fields: ["status", "branch", "department", "designation", "image"],
	filters: [["status", "=", "Active"]],
	get_indicator(doc) {
		return [
			__(doc.status, null, "Employee"),
			{ Active: "green", Inactive: "red", Left: "gray", Suspended: "orange" }[doc.status],
			"status,=," + doc.status,
		];
	},

	onload(listview) {
		if (frappe.perm.has_perm("Employee", 0, "create")) {
			frappe.db.count("Employee").then((count) => {
				if (count === 0) {
					listview.page.add_inner_button(__("Import Employees"), () => {
						frappe.new_doc("Data Import", {
							reference_doctype: "Employee",
						});
					});
				}
			});
		}
	},
};
