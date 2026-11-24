// Every active status has a colour; Cancelled stays grey. Overdue is set by the system when the
// end date passes, so it keeps the red the Task list gives it.
const STATUS_THEMES = {
	Open: "blue",
	Working: "amber",
	"Pending Review": "violet",
	Overdue: "red",
	Completed: "green",
	Cancelled: "gray",
	Template: "gray",
};

export const status_theme = (status) => STATUS_THEMES[status] || "gray";

export const PRIORITY_ICONS = {
	Urgent: "lucide-circle-alert",
	High: "lucide-signal-high",
	Medium: "lucide-signal-medium",
	Low: "lucide-signal-low",
};

export const is_done = (task) => task.status === "Completed" || task.status === "Cancelled";

// The sortable columns. `first` is the direction a column sorts in when first clicked.
export const SORTS = {
	subject: { first: "asc", get: (task) => (task.subject || "").toLowerCase() || null },
	status: { first: "asc", select: true },
	priority: { first: "desc", select: true },
	exp_start_date: { first: "asc", get: (task) => task.exp_start_date || null },
	exp_end_date: { first: "asc", get: (task) => task.exp_end_date || null },
	progress: { first: "desc", get: (task) => task.progress ?? null },
};

export const DEFAULT_SORT = { field: "exp_end_date", dir: "asc" };

/**
 * A compare function for `sort`, with the rules the Tasks tab has always had: a Select field
 * sorts by its options (Priority runs Low to Urgent, Status follows the workflow), empty values
 * come last either way, and ties keep the order the tasks were created in.
 */
export function sorter(sort, options = {}) {
	const spec = SORTS[sort.field];
	const order = spec.select ? options[sort.field] || [] : null;
	const get = spec.select
		? (task) => {
				const position = order.indexOf(task[sort.field]);
				return task[sort.field] && position >= 0 ? position : null;
		  }
		: spec.get;
	const sign = sort.dir === "asc" ? 1 : -1;

	return (a, b) => {
		const x = get(a);
		const y = get(b);
		if (x === null || y === null) {
			if (x !== y) return x === null ? 1 : -1;
		} else {
			const diff = typeof x === "number" ? x - y : String(x).localeCompare(String(y));
			if (diff) return sign * diff;
		}
		return String(a.creation).localeCompare(String(b.creation));
	};
}

export function next_sort(sort, field) {
	if (sort.field !== field) return { field, dir: SORTS[field].first };
	return { field, dir: sort.dir === "asc" ? "desc" : "asc" };
}
