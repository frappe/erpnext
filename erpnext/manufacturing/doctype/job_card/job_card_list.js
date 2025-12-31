frappe.listview_settings["Job Card"] = {
	has_indicator_for_draft: true,
	add_fields: ["expected_start_date", "expected_end_date", "operation"],
	get_indicator: function(doc) {
		const status_colors = {
			"Work In Progress": "orange",
			Completed: "green",
			Cancelled: "red",
			"Material Transferred": "blue",
			Open: "red",
		};
		const status = doc.status || "Open";
		const color = status_colors[status] || "blue";

		return [__(status), color, `status,=,${status}`];
	},

	button: {
		show(doc) {
			const operation = (doc.operation || "").toLowerCase();
			return operation.includes("mixing2") || operation.includes("mixing") || operation.includes("distribution");
		},
		get_label(doc) {
			const operation = (doc.operation || "").toLowerCase();
			if (operation.includes("mixing2") || operation.includes("mixing")) {
				return __('Open Mixer');
			}
			else if (operation.includes("distribution")) {
				return __('Open Distribution');
			}
			return __('Open Station')
		},
		get_description(doc) {
			const operation = (doc.operation || "").toLowerCase();
			if (operation.includes("mixing2") || operation.includes("mixing")) {
				return __('Open Mixer Station for {0}', [doc.name]);
			}
			else if (operation.includes("distribution")) {
				return __('Open Distribution Station for {0}', [doc.name]);
			}
			return __('Open Station for {0}', [doc.name]);
		},
		action(doc) {
			const operation = (doc.operation || "").toLowerCase();
			if (operation.includes("mixing2") || operation.includes("mixing")) {
				frappe.set_route('mixer-station', doc.name);
			}
			else if (operation.includes("distribution")) {
				frappe.set_route('operator-station', doc.name);
			}
			frappe.set_route('operator-station', doc.name);
		}
	}
};
