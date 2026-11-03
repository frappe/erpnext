import { __ } from "./api";

const nf = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });

export const fmt = (n) => nf.format(Number(n) || 0);
export const num = (v) => Number(v) || 0;
export const round = (n, d = 2) => Math.round(n * 10 ** d) / 10 ** d;
export const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
export const plural = (unit) => (unit && !unit.endsWith("s") ? `${unit}s` : unit || __("units"));

export function fmtTimer(total) {
	const pad = (n) => String(n).padStart(2, "0");
	return `${pad(Math.floor(total / 3600))}:${pad(Math.floor((total % 3600) / 60))}:${pad(total % 60)}`;
}
