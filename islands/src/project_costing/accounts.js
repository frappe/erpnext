const __ = window.__;

// How each account stands against its budget, as `account_status` in accounts.py names it.
export const ACCOUNT_STATUS = {
	ok: { label: __("On track"), theme: "green" },
	near: { label: __("Near limit"), theme: "amber" },
	over_committed: { label: __("Over with orders"), theme: "amber" },
	blocked: { label: __("Orders stopped"), theme: "red" },
	over: { label: __("Over budget"), theme: "red" },
	none: { label: __("No budget"), theme: "gray" },
};

const STAGES = {
	"Material Request": __("from request"),
	"Purchase Order": __("from order"),
	Expense: __("on expense"),
};

/** The Accounts view of the payload: rows split by root type, with totals across them. */
export function toAccountsView(payload) {
	const expense = payload.rows.filter((row) => row.root_type === "Expense");
	const income = payload.rows.filter((row) => row.root_type === "Income");
	const budgeted = expense.filter((row) => row.budget);
	const sum = (rows, read) => rows.reduce((total, row) => total + (read(row) || 0), 0);
	const actual = sum(expense, (row) => row.actual);
	const income_actual = sum(income, (row) => row.actual);
	const budget = sum(budgeted, (row) => row.budget.amount);
	return {
		...payload,
		expense,
		income,
		budget_count: budgeted.length,
		budget: budgeted.length ? budget : null,
		budgeted_actual: sum(budgeted, (row) => row.actual),
		actual,
		committed: sum(expense, (row) => row.committed),
		available: budgeted.length ? budget - sum(budgeted, (row) => row.actual + row.committed) : null,
		income_actual,
		profit: income_actual - actual,
		has_entries: payload.rows.some((row) => row.entries),
	};
}

/** How the account's Budget acts when exceeded, for the line under its name; "" without one. */
export function accountMeta(row) {
	const control = row.budget?.control;
	if (control) return __("{0} {1}", [__(control.action), STAGES[control.stage]]);
	return row.budget ? __("Track only") : "";
}

export function accountKpis(accounts, format, { internal }) {
	const has = accounts.budget_count > 0;
	const kpis = [
		{
			label: __("Budget"),
			value: has ? format.short(accounts.budget) : __("Not set"),
			sub: has
				? count(accounts.budget_count, __("1 account"), __("{0} accounts", [accounts.budget_count]))
				: null,
		},
		{
			label: __("Actual"),
			value: format.short(accounts.actual),
			sub: has
				? __("{0} of budget", [format.percent((accounts.budgeted_actual / accounts.budget) * 100)])
				: null,
			hint: __("Ledger expense; timesheets do not post here"),
		},
		// Available already takes out what is committed, so Committed gets a card of its own only
		// when there is no budget to measure it against.
		has
			? {
					label: __("Available"),
					value: format.short(accounts.available),
					sub: accounts.committed
						? __("after {0} committed", [format.short(accounts.committed)])
						: null,
					hint: __("Budget − actual − committed"),
			  }
			: {
					label: __("Committed"),
					value: format.short(accounts.committed),
					hint: __("Open purchase orders + material requests"),
			  },
	];
	if (!internal)
		kpis.push({
			label: __("Ledger profit"),
			value: format.short(accounts.profit),
			sub: accounts.income_actual
				? __("{0} of income", [format.percent((accounts.profit / accounts.income_actual) * 100)])
				: null,
		});
	return kpis;
}

// The singular and plural strings, each translated whole.
const count = (number, one, many) => (number === 1 ? one : many);

/** The desk route for a new Budget on the project, prefilled. */
export function newBudgetRoute(accounts, account) {
	const options = { budget_against: "Project", project: accounts.project, company: accounts.company };
	if (account) options.account = account;
	return `Form/Budget/new?${new URLSearchParams(options)}`;
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
	return `query-report/General Ledger?${new URLSearchParams(filters)}`;
}
