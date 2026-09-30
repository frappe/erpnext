// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.views.calendar["Work Order"] = {
	fields: ["planned_start_date", "planned_end_date", "status", "produced_qty", "qty", "name", "name"],
	field_map: {
		start: "planned_start_date",
		end: "planned_end_date",
		id: "name",
		title: "name",
		status: "status",
		allDay: "allDay",
		progress: function (data) {
			return (flt(data.produced_qty) / data.qty) * 100;
		},
	},
	gantt: true,
	get_css_class: function (data) {
		if (data.status === "Completed") {
			return "success";
		} else if (data.status === "In Process") {
			return "warning";
		} else {
			return "danger";
		}
	},
	filters: [
		{
			fieldtype: "Link",
			fieldname: "sales_order",
			options: "Sales Order",
			label: __("Sales Order"),
		},
		{
			fieldtype: "Link",
			fieldname: "production_item",
			options: "Item",
			label: __("Production Item"),
		},
		{
			fieldtype: "Link",
			fieldname: "wip_warehouse",
			options: "Warehouse",
			label: __("WIP Warehouse"),
		},
	],
	get_events_method: "frappe.desk.calendar.get_events",
};

const WORK_ORDER_GANTT_COLORS = {
	Draft: "red",
	Stopped: "red",
	"Not Started": "red",
	"In Process": "orange",
	Completed: "green",
	"Stock Reserved": "blue",
	"Stock Partially Reserved": "orange",
	Cancelled: "gray",
};

if (!frappe.views.GanttView.prototype._work_order_status_colors) {
	frappe.views.GanttView.prototype._work_order_status_colors = true;

	const prepare_tasks = frappe.views.GanttView.prototype.prepare_tasks;
	frappe.views.GanttView.prototype.prepare_tasks = function () {
		prepare_tasks.call(this);
		if (this.doctype === "Work Order") {
			set_work_order_bar_classes(this);
		}
	};

	const set_colors = frappe.views.GanttView.prototype.set_colors;
	frappe.views.GanttView.prototype.set_colors = function () {
		set_colors.call(this);
		if (this.doctype === "Work Order") {
			set_work_order_bar_styles(this);
		}
	};
}

function set_work_order_bar_classes(view) {
	view.tasks.forEach((task, idx) => {
		const color = WORK_ORDER_GANTT_COLORS[view.data[idx].status];
		if (color) {
			task.custom_class = "wo-" + color;
		}
	});
}

function set_work_order_bar_styles(view) {
	const style = [...new Set(Object.values(WORK_ORDER_GANTT_COLORS))]
		.map(
			(color) => `
			.gantt .bar-wrapper.wo-${color} .bar {
				fill: var(--${color}-300);
			}
			.gantt .bar-wrapper.wo-${color} .bar-progress {
				fill: var(--${color}-300);
			}
		`
		)
		.join("");

	view.$result.prepend(`<style>${style}</style>`);
}
