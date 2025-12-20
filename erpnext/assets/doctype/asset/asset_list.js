frappe.listview_settings["Asset"] = {
	add_fields: ["status", "docstatus"],
	has_indicator_for_draft: 1,
	get_indicator: function (doc) {
		if (doc.status === "Fully Depreciated") {
			return [__("Fully Depreciated"), "green", "status,=,Fully Depreciated"];
		} else if (doc.status === "Partially Depreciated") {
			return [__("Partially Depreciated"), "grey", "status,=,Partially Depreciated"];
		} else if (doc.status === "Sold") {
			return [__("Sold"), "green", "status,=,Sold"];
		} else if (doc.status === "Work In Progress") {
			return [__("Work In Progress"), "orange", "status,=,Work In Progress"];
		} else if (doc.status === "Capitalized") {
			return [__("Capitalized"), "grey", "status,=,Capitalized"];
		} else if (doc.status === "Scrapped") {
			return [__("Scrapped"), "grey", "status,=,Scrapped"];
		} else if (doc.status === "In Maintenance") {
			return [__("In Maintenance"), "orange", "status,=,In Maintenance"];
		} else if (doc.status === "Out of Order") {
			return [__("Out of Order"), "grey", "status,=,Out of Order"];
		} else if (doc.status === "Issue") {
			return [__("Issue"), "orange", "status,=,Issue"];
		} else if (doc.status === "Receipt") {
			return [__("Receipt"), "green", "status,=,Receipt"];
		} else if (doc.status === "Submitted") {
			return [__("Submitted"), "blue", "status,=,Submitted"];
		} else if (doc.status === "Draft" || doc.docstatus === 0) {
			return [__("Draft"), "red", "status,=,Draft"];
		}
	},
	onload: function (me) {
		me.page.add_action_item(__("Make Asset Movement"), function () {
			const assets = me.get_checked_items();
			frappe.call({
				method: "erpnext.assets.doctype.asset.asset.make_asset_movement",
				freeze: true,
				args: {
					assets: assets,
				},
				callback: function (r) {
					if (r.message) {
						var doc = frappe.model.sync(r.message)[0];
						frappe.set_route("Form", doc.doctype, doc.name);
					}
				},
			});
		});
	},
};
