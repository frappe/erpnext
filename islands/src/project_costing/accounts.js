import { report_route } from "./costing.js";

const __ = window.__;

// How each account stands against its budget, as `account_status` in budgets.py names it.
export const ACCOUNT_STATUS = {
	ok: { label: __("On track"), theme: "green" },
	over_to_date: { label: __("Over budget to date"), theme: "amber" },
	over: { label: __("Over budget"), theme: "amber" },
	blocked: { label: __("Spending blocked"), theme: "red" },
	none: { label: __("No budget"), theme: "gray" },
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
		// a Budget over several fiscal years counts what its earlier years spent too
		budgeted_spent: sum(budgeted, (row) => row.budget.spent),
		unbudgeted: sum(expense, (row) => (row.budget ? 0 : row.actual)),
		income_actual: sum(income, (row) => row.actual),
		actual,
		committed: sum(expense, (row) => row.committed),
		available: budgeted.length ? sum(budgeted, (row) => row.budget.available) : null,
		has_entries: payload.rows.some((row) => row.entries),
	};
}

/** How the account's Budget acts when exceeded, for the line under its name; "" without one. */
export function accountMeta(row) {
	return row.budget?.rule || "";
}

/**
 * The Accounts cards. Budgets are optional and most projects have none: then the cards answer what
 * the books recorded, with three real numbers and no word about a missing budget. Adding one stays
 * on the chart's header.
 */
export function accountKpis(accounts, format) {
	const actual = {
		label: __("Spent"),
		value: format.short(accounts.actual),
		sub: actual_caption(accounts, format),
		hint: accounts.budget_count
			? __(
					"Ledger expense this fiscal year; timesheets don't post here · Budget share counts the budget's whole period"
			  )
			: __("Ledger expense this fiscal year; timesheets don't post here"),
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
		},
		actual,
		// Available already takes out what is committed, so Committed shows as its caption.
		{
			label: __("Available"),
			value: format.short(accounts.available),
			sub: accounts.committed ? __("after {0} committed", [format.short(accounts.committed)]) : null,
			hint: __("Budget − spent − committed"),
		},
	];
}

/**
 * What Spent is measured against. A share of the budget only holds when every account with spend
 * has a budget; otherwise the caption says how much sits outside them, so the share isn't read
 * against a total that includes it. Without a budget there is nothing to measure against.
 */
function actual_caption(accounts, format) {
	if (!accounts.budget_count) return null;
	// when none of it is on a budgeted account, the amount would only repeat the card's value
	if (accounts.unbudgeted > 0 && accounts.unbudgeted >= accounts.actual) return __("All without a budget");
	if (accounts.unbudgeted) return __("{0} without a budget", [format.short(accounts.unbudgeted)]);
	return __("{0} of budget", [format.percent((accounts.budgeted_spent / accounts.budget) * 100)]);
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

/** The General Ledger report, filtered to the project. */
export function ledgerReportRoute(accounts) {
	const filters = {
		company: accounts.company,
		from_date: accounts.from_date,
		to_date: accounts.to_date,
		project: accounts.project,
	};
	return report_route("General Ledger", filters);
}
