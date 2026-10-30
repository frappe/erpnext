import { inject, provide } from "vue";

const FORMAT = Symbol("costing-format");

/**
 * Number formatting for the Costing tab, in the company's currency, which `get_currency` reads
 * from the latest payload.
 *
 * Desk prints amounts in its own number format, so the host's formatters come first. A host
 * without them, such as a unit test, gets the browser's.
 */
export function createFormat(host, get_currency) {
	const locale = host.locale || undefined;
	const plain = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
	const month_name = new Intl.DateTimeFormat(locale, { month: "short", year: "2-digit", timeZone: "UTC" });
	const browser_date = new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeZone: "UTC" });
	const currency_field = { fieldtype: "Currency", options: "currency", precision: 0 };

	const browser_currency = (value, currency, compact) =>
		new Intl.NumberFormat(locale, {
			style: "currency",
			currency,
			notation: compact ? "compact" : "standard",
			maximumFractionDigits: compact ? 1 : 0,
		}).format(value);

	// A negative amount as "−₹ 200", not "₹ -200": the sign reads first.
	const signed = (value, render) => {
		if (value == null) return "—";
		const rounded = Math.round(value);
		return rounded < 0 ? `−${render(-rounded)}` : render(rounded);
	};

	return {
		money: (value, currency = get_currency()) =>
			signed(value, (amount) =>
				host.format
					? host.format(amount, currency_field, { currency })
					: browser_currency(amount, currency, false)
			),
		// An amount shortened, such as "₹ 1.2 L".
		short: (value, currency = get_currency()) =>
			signed(value, (amount) =>
				host.format_axis_number
					? host.format_axis_number(amount, currency_field, { currency })
					: browser_currency(amount, currency, true)
			),
		number: (value) => plain.format(value || 0),
		percent: (value, digits = 0) => (value == null ? "—" : `${Number(value).toFixed(digits)}%`),
		// "2026-03" as "Mar 26"
		month: (key) => month_name.format(new Date(`${key}-01T00:00:00Z`)),
		// A "YYYY-MM-DD" date in the user's date format
		date: (date) =>
			host.format
				? host.format(date, { fieldtype: "Date" })
				: browser_date.format(new Date(`${date}T00:00:00Z`)),
	};
}

export const provideFormat = (format) => provide(FORMAT, format);
export const useFormat = () => inject(FORMAT);
