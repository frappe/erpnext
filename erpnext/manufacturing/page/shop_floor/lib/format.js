const nf = new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 });

export const fmt = (n) => nf.format(Number(n) || 0);
export const num = (v) => Number(v) || 0;

export function fmtDuration(seconds) {
	const minutes = Math.max(0, Math.floor(seconds / 60));
	const hours = Math.floor(minutes / 60);
	return hours ? window.__("{0} h {1} min", [hours, minutes % 60]) : window.__("{0} min", [minutes]);
}

export const timeOf = (value) =>
	value ? window.frappe.datetime.str_to_user(value).split(" ").pop().slice(0, 5) : "";
