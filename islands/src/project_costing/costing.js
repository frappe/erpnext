const __ = window.__;

const PHASES = { Open: "open", "On hold": "hold", Completed: "completed", Cancelled: "cancelled" };

/** Each cost source, the list view its entries open in, and the access flag that opens it. */
export const SOURCES = [
	{
		key: "labour",
		label: __("Labour"),
		via: __("timesheets"),
		route: (project) => list_route("Timesheet", { "Timesheet Detail.project": project, docstatus: 1 }),
	},
	{
		key: "purchases",
		label: __("Purchases"),
		via: __("purchase invoices"),
		access: "purchases",
		route: (project) =>
			list_route("Purchase Invoice", { "Purchase Invoice Item.project": project, docstatus: 1 }),
	},
	{
		key: "materials",
		label: __("Materials"),
		via: __("stock consumption"),
		access: "materials",
		// the stock ledger rows the total is read from: stock entries, delivery notes and sales
		// invoices that take stock out for the project
		route: (project) =>
			list_route("Stock Ledger Entry", {
				project,
				is_cancelled: 0,
				voucher_type: ["in", ["Stock Entry", "Delivery Note", "Sales Invoice"]],
			}),
	},
	{
		key: "expenses",
		label: __("Expenses"),
		via: __("expense claims"),
		route: (project) => list_route("Expense Claim", { project, docstatus: 1 }),
	},
];

/** A desk route to `doctype`'s list, filtered. A `Child DocType.field` key filters on a child table. */
export function list_route(doctype, filters) {
	// an operator filter, such as ["in", [...]], travels as JSON, as the list view reads it
	const values = Object.entries(filters).map(([key, value]) => [
		key,
		typeof value === "string" ? value : JSON.stringify(value),
	]);
	return `List/${doctype}?${new URLSearchParams(values)}`;
}

export const form_route = (doctype, name) => `Form/${doctype}/${name}`;

/** A query report's route, opened with `filters` set. */
export const report_route = (report, filters) => `query-report/${report}?${new URLSearchParams(filters)}`;

/**
 * The Costing tab's payload, with what the cards derive from it worked out once.
 *
 * `doc` is the Project as the form holds it, for the fields the payload does not carry.
 */
export function toView(payload, doc) {
	const summary = payload.summary;
	const phase = PHASES[summary.status] || "open";
	const labour_cost = summary.sources.labour || 0;
	return {
		...summary,
		project: payload.project,
		customer: doc.customer,
		customer_name: payload.customer_name,
		expected_end_date: doc.expected_end_date,
		access: payload.access,
		phase,
		closed: phase === "completed" || phase === "cancelled",
		has_estimate: summary.estimate != null,
		has_contract: summary.contract != null,
		hrms: "expenses" in summary.sources,
		rate: summary.hours ? labour_cost / summary.hours : 0,
		sources: sources_of(summary),
		months: payload.monthly || [],
		billing: payload.billing,
		drivers: payload.drivers,
		rate_gaps: payload.rate_gaps,
		labour_understated: Boolean(payload.rate_gaps?.understated),
	};
}

function sources_of(summary) {
	return SOURCES.filter((source) => source.key in summary.sources).map((source) => ({
		...source,
		amount: summary.sources[source.key],
	}));
}
