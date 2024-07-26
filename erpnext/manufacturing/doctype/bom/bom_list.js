frappe.listview_settings["BOM"] = {
	add_fields: ["is_active", "is_default", "total_cost", "has_variants"],
	get_indicator: function (doc) {
		if (doc.is_active && doc.has_variants) {
			return [__("Template"), "orange", "has_variants,=,Yes"];
		} else if (doc.is_default) {
			return [__("Default"), "green", "is_default,=,Yes"];
		} else if (doc.is_active) {
			return [__("Active"), "blue", "is_active,=,Yes"];
		} else if (!doc.is_active) {
			return [__("Not active"), "gray", "is_active,=,No"];
		}
	},
};

frappe.help.youtube_id["BOM"] = "hDV0c1OeWLo";
