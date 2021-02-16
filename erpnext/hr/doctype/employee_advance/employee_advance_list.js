frappe.listview_settings['Employee Advance'] = {
	add_fields: ["status"],
	get_indicator: function(doc) {
		if (doc.status == "Deducted from Salary") {
			return [__("Deducted from Salary"), "green", "status,=,Deducted from Salary"];
        } else if(doc.status == "Claimed") {
			return [__("Claimed"), "green", "status,=,Claimed"];
		} else if(doc.status == "Unclaimed") {
			return [__("Unclaimed"), "orange", "status,=,Unclaimed"];
		} else if(doc.status == "Unpaid") {
			return [__("Unpaid"), "red", "status,=,Unpaid"];
		}
	},

	onload: function (listview) {
		listview.page.add_action_item(__("Create Payment"), function () {
			var names = listview.get_checked_items(true);

			if (names && names.length) {
				return frappe.call({
					method: "erpnext.hr.doctype.employee_advance.employee_advance.make_multiple_bank_entries",
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
