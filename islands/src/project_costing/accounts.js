import { report_route } from "./costing.js";

const __ = window.__;

// How each account stands against its budget, as `account_status` in accounts.py names it.
export const ACCOUNT_STATUS = {
	ok: { label: __("On track"), theme: "green" },
	near: { label: __("Near limit"), theme: "amber" },
	over_committed: { label: __("Over with open orders"), theme: "amber" },
	blocked: { label: __("New orders blocked"), theme: "red" },
	requests_blocked: { label: __("New requests blocked"), theme: "red" },
	over: { label: __("Over budget"), theme: "red" },
	none: { label: __("No budget"), theme: "gray" },
};

// What a Budget does once exceeded, by its action and the earliest stage it checks.
const CONTROLS = {
	Stop: {
		"Material Request": __("Blocks new requests"),
		"Purchase Order": __("Blocks new orders"),
		Expense: __("Blocks expenses"),
	},
	Warn: {
		"Material Request": __("Warns on requests"),
		"Purchase Order": __("Warns on orders"),
		Expense: __("Warns on expenses"),
	},
};

/** The Accounts view of the payload: rows split by root type, with totals across them. */
export function toAccountsView(payload) {
	const expense = payload.rows.filter((row) => row.root_type === "Expense");
	const income = payload.rows.filter((row) => row.root_type === "Income");
	const budgeted = expense.filter((row) => row.budget);
	const sum = (rows, read) => rows.reduce((total, row) => total + (read(row) || 0), 0);
	const actual = sum(expense, (row) => row.actual);
	const budget = sum(budgeted, (row) => row.budget.amount);
	return {
		...payload,
		expense,
		income,
		budget_count: budgeted.length,
		budget: budgeted.length ? budget : null,
		budgeted_actual: sum(budgeted, (row) => row.actual),
		unbudgeted: sum(expense, (row) => (row.budget ? 0 : row.actual)),
		income_actual: sum(income, (row) => row.actual),
		actual,
		committed: sum(expense, (row) => row.committed),
		available: budgeted.length ? budget - sum(budgeted, (row) => row.actual + row.committed) : null,
		has_entries: payload.rows.some((row) => row.entries),
	};
}

/** How the account's Budget acts when exceeded, for the line under its name; "" without one. */
export function accountMeta(row) {
	const control = row.budget?.control;
	if (control) return CONTROLS[control.action][control.stage];
	return row.budget ? __("Tracks only") : "";
}

/**
 * The Accounts cards. Budgets are optional and most projects have none: then the cards answer what
 * the books recorded, with three real numbers and no word about a missing budget. Adding one stays
 * on the chart's header.
 */
export function accountKpis(accounts, format, { has_labour = false } = {}) {
	const actual = {
		label: __("Actual"),
		value: format.short(accounts.actual),
		sub: actual_caption(accounts, format, has_labour),
		hint: __("Ledger expense this fiscal year; timesheets don't post here"),
	};
	if (!accounts.budget_count)
		return [
			actual,
			{
				label: __("Committed"),
				value: format.short(accounts.committed),
				hint: __("Open purchase orders + material requests"),
			},
			{
				label: __("Income"),
				value: format.short(accounts.income_actual),
				hint: __("Ledger income this fiscal year; mostly sales invoices"),
			},
		];
	return [
		{
			label: __("Budget"),
			value: format.short(accounts.budget),
			sub: count(accounts.budget_count, __("1 account"), __("{0} accounts", [accounts.budget_count])),
		},
		actual,
		// Available already takes out what is committed, so Committed shows as its caption.
		{
			label: __("Available"),
			value: format.short(accounts.available),
			sub: accounts.committed ? __("after {0} committed", [format.short(accounts.committed)]) : null,
			hint: __("Budget − actual − committed"),
		},
	];
}

/**
 * What Actual is measured against. A share of the budget only holds when every account with spend
 * has a budget; otherwise the caption says how much sits outside them, so the share isn't read
 * against a total that includes it. With no budget, it says that timesheet labour is left out,
 * when the project has any.
 */
function actual_caption(accounts, format, has_labour) {
	if (!accounts.budget_count) return has_labour ? __("Excludes timesheet labour") : null;
	if (accounts.unbudgeted) return __("{0} without a budget", [format.short(accounts.unbudgeted)]);
	return __("{0} of budget", [format.percent((accounts.budgeted_actual / accounts.budget) * 100)]);
}

// The singular and plural strings, each translated whole.
const count = (number, one, many) => (number === 1 ? one : many);

/** The desk route for a new Budget on the project, prefilled. */
export function newBudgetRoute(accounts, account) {
	const options = { budget_against: "Project", project: accounts.project, company: accounts.company };
	if (account) options.account = account;
	return `Form/Budget/new?${new URLSearchParams(options)}`;
}

/**
 * The finance reports for the project's fiscal year that the user may open, as Reports menu
 * items: [label, route].
 */
export function accountsReports(accounts) {
	const year = {
		company: accounts.company,
		from_fiscal_year: accounts.fiscal_year,
		to_fiscal_year: accounts.fiscal_year,
	};
	const routes = {
		"General Ledger": ledgerReportRoute(accounts),
		"Profit and Loss Statement": report_route("Profit and Loss Statement", {
			...year,
			project: accounts.project,
		}),
	};
	// the variance report lists Budget records
	if (accounts.access.budgets)
		routes["Budget Variance Report"] = report_route("Budget Variance Report", {
			...year,
			budget_against: "Project",
			budget_against_filter: accounts.project,
		});
	return accounts.reports.filter((report) => routes[report]).map((report) => [__(report), routes[report]]);
}

/** The General Ledger report, filtered to the project, and to one account when given. */
export function ledgerReportRoute(accounts, account) {
	const filters = {
		company: accounts.company,
		from_date: accounts.from_date,
		to_date: accounts.to_date,
		project: accounts.project,
	};
	if (account) filters.account = account;
	return report_route("General Ledger", filters);
}
