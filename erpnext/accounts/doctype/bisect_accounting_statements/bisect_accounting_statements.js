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
		const day = (value) => value?.slice(0, 10);
		const [from_date, to_date, current_from_date, current_to_date] = [
			frm.doc.from_date,
			frm.doc.to_date,
			frm.doc.current_from_date,
			frm.doc.current_to_date,
		].map(day);
		const days = [];
		for (let date = from_date; date <= to_date; date = day(frappe.datetime.add_days(date, 1))) {
			days.push({ date, bisecting: current_from_date <= date && date <= current_to_date ? 1 : 0 });
		}

		const config = {
			type: "calendar-heatmap",
			data: days,
			date: "date",
			value: "bisecting",
			start: from_date,
			end: to_date,
			fieldtype: "Int",
			height: 200,
		};
		if (frm.bisect_heatmap) {
			frm.bisect_heatmap.update(config);
		} else {
			frm.bisect_heatmap = frappe.ui.chart(frm.get_field("bisect_heatmap").$wrapper, config);
		}
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
