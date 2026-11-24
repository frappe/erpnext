import { inject, provide } from "vue";

const FORMAT = Symbol("overview-format");

export function createFormat(host) {
	const __ = window.__;
	const moment = window.moment;
	const locale = host.locale || undefined;

	const number = (value, decimals = 0) =>
		host.format
			? host.format(value || 0, { fieldtype: "Float", precision: decimals })
			: new Intl.NumberFormat(locale, { maximumFractionDigits: decimals }).format(value || 0);
	const auto = (value) => number(value, value % 1 ? 1 : 0);

	return {
		number,
		percent: (value) => `${auto(value)}%`,
		hours: (hours) => __("{0} h", [auto(hours)]),
		money: (value, currency) =>
			host.format
				? host.format(
						value,
						{ fieldtype: "Currency", options: "currency", precision: 0 },
						{ currency }
				  )
				: new Intl.NumberFormat(locale, {
						style: "currency",
						currency,
						maximumFractionDigits: 0,
				  }).format(value),
		date: (date, pattern) => moment(date).format(pattern),
		days_late: (days) => (days === 1 ? __("1 day late") : __("{0} days late", [days])),
		days_early: (days) => (days === 1 ? __("1 day early") : __("{0} days early", [days])),
	};
}

export const provideFormat = (format) => provide(FORMAT, format);
export const useFormat = () => inject(FORMAT);
