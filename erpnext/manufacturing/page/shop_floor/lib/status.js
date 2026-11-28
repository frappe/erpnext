import { __ } from "./api";
import { fmt } from "./format";

export const STATION_THEME = {
	Production: "green",
	Idle: "gray",
	Off: "gray",
	Problem: "red",
	Maintenance: "amber",
	Setup: "blue",
};
export const STATION_DOT = {
	Production: "bg-surface-green-7",
	Idle: "bg-surface-gray-5",
	Off: "bg-surface-gray-5",
	Problem: "bg-surface-red-7",
	Maintenance: "bg-surface-amber-7",
	Setup: "bg-surface-blue-7",
};

const PHASES = {
	running: { label: "Work In Progress", theme: "blue" },
	paused: { label: "On Hold", theme: "amber" },
	done: { label: "Ready to Submit", theme: "green" },
	open: { label: "Open", theme: "gray" },
};

export const phaseOf = (jobCard) => {
	const phase = PHASES[jobCard.phase] || PHASES.open;
	return { label: __(phase.label), theme: phase.theme };
};

export const progressText = (jobCard) =>
	__("{0} of {1} {2} done", [
		fmt(jobCard.total_completed_qty),
		fmt(jobCard.for_quantity),
		jobCard.stock_uom || "",
	]);

export function stationSummary(workstation) {
	const job = workstation.current;
	if (workstation.status === "Problem")
		return { text: __("Stopped for a breakdown"), tone: "text-ink-red-5" };
	if (workstation.status === "Maintenance")
		return { text: __("Under maintenance"), tone: "text-ink-amber-5" };
	if (job?.phase === "paused")
		return { text: __("On hold · {0}", [job.operation]), tone: "text-ink-amber-5" };
	if (job) return { text: `${job.operation} · ${progressText(job)}`, tone: "text-ink-gray-7" };
	if (workstation.queue_count)
		return { text: __("{0} job cards waiting", [workstation.queue_count]), tone: "text-ink-blue-5" };
	return { text: __("No job cards"), tone: "text-ink-gray-5" };
}

export function machineMode(workstation) {
	if (workstation.status === "Problem") return "down";
	if (workstation.current?.phase === "paused") return "hold";
	if (workstation.current) return "run";
	return "off";
}
