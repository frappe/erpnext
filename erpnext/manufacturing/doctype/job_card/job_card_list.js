frappe.listview_settings["Job Card"] = {
	has_indicator_for_draft: true,
	add_fields: ["expected_start_date", "expected_end_date", "operation"],
	get_indicator: function (doc) {
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
			const operation = (doc.operation || "").trim().toLowerCase();
			return operation.includes("mixing2") || operation.includes("mixing") || operation.includes("distribution") || operation.includes("pressing") || operation.includes("cooling") || operation.includes("trimming") || operation.includes("polishing") || operation.includes("callibration");
		},
		get_label(doc) {
			const operation = (doc.operation || "").trim().toLowerCase();
			if (operation.includes("mixing")) return __('Open Mixer');
			if (operation.includes("distribution")) return __('Open Distribution');
			if (operation.includes("pressing")) return __('Open Pressing');
			if (operation.includes("cooling")) return __('Open Cooling');
			if (operation.includes("trimming")) return __('Open Trimming');
			if (operation.includes("polishing")) return __('Open Polishing');
			if (operation.includes("callibration")) return __('Open Calibration');
			return __('Open Station');
		},
		get_description(doc) {
			const operation = (doc.operation || "").trim().toLowerCase();
			if (operation.includes("mixing2") || operation.includes("mixing")) {
				return __('Open Mixer Station for {0}', [doc.name]);
			}
			else if (operation.includes("distribution")) {
				return __('Open Distribution Station for {0}', [doc.name]);
			}
			else if (operation.includes("pressing")) {
				return __('Open Pressing Station for {0}', [doc.name]);
			}
			else if (operation.includes("cooling")) {
				return __('Open Cooling Station for {0}', [doc.name]);
			}
			else if (operation.includes("trimming")) {
				return __('Open Trimming Station for {0}', [doc.name]);
			}
			else if (operation.includes("polishing")) {
				return __('Open Polishing Station for {0}', [doc.name]);
			}
			else if (operation.includes("callibration")) {
				return __('Open Calibration Station for {0}', [doc.name]);
			}
			return __('Open Station for {0}', [doc.name]);
		},
		action(doc) {
			const operation = (doc.operation || "").trim().toLowerCase();
			let station_page, station_type;
			if (operation.includes("mixing2") || operation.includes("mixing")) {
				station_page = 'mixer-station';
			}
			else if (operation.includes("distribution")) {
				station_page = 'operator-station';
				station_type = 'distribution';
			}
			else if (operation.includes("pressing")) {
				station_page = 'operator-station';
				station_type = 'pressing';
			}
			else if (operation.includes("cooling")) {
				station_page = 'operator-station';
				station_type = 'cooling';
			}
			else if (operation.includes("trimming")) {
				station_page = 'operator-station';
				station_type = 'trimming';
			}
			else if (operation.includes("polishing")) {
				station_page = 'operator-station';
				station_type = 'polishing';
			}
			else if (operation.includes("callibration")) {
				station_page = 'operator-station';
				station_type = 'callibration';
			}
			else {
				station_page = 'operator-station';
				station_type = 'operator';
			}
			frappe.set_route(station_page, station_type || '', doc.name);
		}
	}
};
