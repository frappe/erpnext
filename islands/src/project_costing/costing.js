const __ = window.__;

const PHASES = { Open: "open", "On hold": "hold", Completed: "completed", Cancelled: "cancelled" };

/** Each cost source, the list view its entries open in, and the access flag that opens it. */
export const SOURCES = [
	{
		key: "labour",
		label: __("Labour"),
		via: __("timesheets"),
		definition: __("Costing amount of submitted timesheets"),
		route: (project) => list_route("Timesheet", { "Timesheet Detail.project": project, docstatus: 1 }),
	},
	{
		key: "purchases",
		label: __("Purchases"),
		via: __("purchase invoices"),
		access: "purchases",
		definition: __("Non-stock items on submitted purchase invoices"),
		route: (project) =>
			list_route("Purchase Invoice", { "Purchase Invoice Item.project": project, docstatus: 1 }),
	},
	{
		key: "materials",
		label: __("Materials"),
		via: __("stock consumption"),
		access: "materials",
		definition: __("Value of stock consumed against the project"),
		route: (project) =>
			list_route("Stock Entry", { "Stock Entry Detail.project": project, docstatus: 1 }),
	},
	{
		key: "expenses",
		label: __("Expenses"),
		via: __("expense claims"),
		definition: __("Sanctioned amount of submitted expense claims"),
		route: (project) => list_route("Expense Claim", { project, docstatus: 1 }),
	},
];

/** A desk route to `doctype`'s list, filtered. A `Child DocType.field` key filters on a child table. */
export function list_route(doctype, filters) {
	return `List/${doctype}?${new URLSearchParams(filters)}`;
}

export const form_route = (doctype, name) => `Form/${doctype}/${name}`;

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
		billing: billing_of(payload.billing, summary),
		drivers: payload.drivers,
		rate_gaps: payload.rate_gaps,
		labour_understated: Boolean(payload.rate_gaps?.understated),
		...margin_percents(summary),
	};
}

function sources_of(summary) {
	return SOURCES.filter((source) => source.key in summary.sources).map((source) => ({
		...source,
		amount: summary.sources[source.key],
	}));
}

function billing_of(billing, summary) {
	if (!billing) return null;
	return {
		...billing,
		over_billed: billing.over_billed ? summary.billed - summary.contract : 0,
		overdue: (billing.invoices || []).some((invoice) => invoice.status === "Overdue"),
	};
}

function margin_percents(summary) {
	const percent_of = (amount, whole) => (amount != null && whole ? (amount * 100) / whole : null);
	return {
		projected_margin_percent: percent_of(
			summary.projected_margin,
			Math.max(summary.contract || 0, summary.billed)
		),
		planned_margin_percent: percent_of(summary.planned_margin, summary.contract),
	};
}
