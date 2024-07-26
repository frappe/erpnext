// Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bisect Accounting Statements", {
	onload(frm) {
		frm.trigger("render_heatmap");
	},
	refresh(frm) {
		frm.add_custom_button(__("Bisect Left"), () => {
			frm.trigger("bisect_left");
		});

		frm.add_custom_button(__("Bisect Right"), () => {
			frm.trigger("bisect_right");
		});

		frm.add_custom_button(__("Up"), () => {
			frm.trigger("move_up");
		});
		frm.add_custom_button(__("Build Tree"), () => {
			frm.trigger("build_tree");
		});
	},
	render_heatmap(frm) {
		let bisect_heatmap = frm.get_field("bisect_heatmap").$wrapper;
		bisect_heatmap.addClass("bisect_heatmap_location");

		// milliseconds in a day
		let msiad = 24 * 60 * 60 * 1000;
		let datapoints = {};
		let fr_dt = new Date(frm.doc.from_date).getTime();
		let to_dt = new Date(frm.doc.to_date).getTime();
		let bisect_start = new Date(frm.doc.current_from_date).getTime();
		let bisect_end = new Date(frm.doc.current_to_date).getTime();

		for (let x = fr_dt; x <= to_dt; x += msiad) {
			let epoch_in_seconds = x / 1000;
			if (bisect_start <= x && x <= bisect_end) {
				datapoints[epoch_in_seconds] = 1.0;
			} else {
				datapoints[epoch_in_seconds] = 0.0;
			}
		}

		new frappe.Chart(".bisect_heatmap_location", {
			type: "heatmap",
			data: {
				dataPoints: datapoints,
				start: new Date(frm.doc.from_date),
				end: new Date(frm.doc.to_date),
			},
			countLabel: "Bisecting",
			discreteDomains: 1,
		});
	},
	bisect_left(frm) {
		frm.call({
			doc: frm.doc,
			method: "bisect_left",
			freeze: true,
			freeze_message: __("Bisecting Left ..."),
			callback: (r) => {
				frm.trigger("render_heatmap");
			},
		});
	},
	bisect_right(frm) {
		frm.call({
			doc: frm.doc,
			freeze: true,
			freeze_message: __("Bisecting Right ..."),
			method: "bisect_right",
			callback: (r) => {
				frm.trigger("render_heatmap");
			},
		});
	},
	move_up(frm) {
		frm.call({
			doc: frm.doc,
			freeze: true,
			freeze_message: __("Moving up in tree ..."),
			method: "move_up",
			callback: (r) => {
				frm.trigger("render_heatmap");
			},
		});
	},
	build_tree(frm) {
		frm.call({
			doc: frm.doc,
			freeze: true,
			freeze_message: __("Rebuilding BTree for period ..."),
			method: "build_tree",
			callback: (r) => {
				frm.trigger("render_heatmap");
			},
		});
	},
});
