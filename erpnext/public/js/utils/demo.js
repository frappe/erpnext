frappe.provide("erpnext.demo");

$(document).on("desktop_screen", function (event, data) {
	data.desktop.add_menu_item({
		label: __("Clear Demo Data"),
		icon: "trash",
		condition: function () {
			return frappe.boot.sysdefaults.demo_company;
		},
		onClick: function () {
			return erpnext.demo.clear_demo();
		},
	});
});

erpnext.demo.clear_demo = function () {
	frappe.confirm(__("Are you sure you want to clear all demo data?"), () => {
		frappe.call({
			method: "erpnext.setup.demo.clear_demo_data",
			freeze: true,
			freeze_message: __("Clearing Demo Data..."),
			callback: function (r) {
				frappe.ui.toolbar.clear_cache();
				frappe.show_alert({
					message: __("Demo data cleared"),
					indicator: "green",
				});
			},
		});
	});
};
