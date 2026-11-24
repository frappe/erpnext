const __ = (...args) => window.__(...args);

// The list's columns, in order. Which show depends on how wide the list is, as the form's sidebar
// takes room too: Task and End date always, then Status and Assigned, then Priority, then Start
// date and Progress, so the task name keeps at least ~200px. A column whose field the user may not
// read is left out.
const COLUMNS = [
	{ field: "subject", label: () => __("Task"), width: "minmax(0,1fr)", from: 0 },
	{ field: "status", label: () => __("Status"), width: "8rem", from: 640 },
	{ field: "priority", label: () => __("Priority"), width: "6rem", from: 760 },
	{ field: "exp_start_date", label: () => __("Start date"), width: "6.5rem", from: 960 },
	{ field: "exp_end_date", label: () => __("End date"), width: "9rem", from: 0 },
	{ field: "progress", label: () => __("Progress"), width: "4.5rem", align: "end", from: 960 },
	{ field: "assigned_to", label: () => __("Assigned"), width: "7rem", unsorted: true, from: 640 },
];

export function visible_columns(fields, width) {
	const readable = new Set(fields);
	return COLUMNS.filter((column) => readable.has(column.field) && width >= column.from);
}

export const grid = (columns) => columns.map((column) => column.width);
