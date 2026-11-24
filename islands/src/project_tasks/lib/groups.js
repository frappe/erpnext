import { is_done } from "./tasks.js";

const __ = (...args) => window.__(...args);

// statuses the system sets, so a task can't be added straight into them
const SYSTEM_STATUSES = ["Overdue", "Template"];
// shown even when empty, so there's always a place to add a task
const ALWAYS_SHOWN = ["Open", "Working"];
// finished groups start folded
export const FOLDED_STATUSES = ["Completed", "Cancelled"];

/** One group per status, in the order of the Status field's options. */
export function status_groups(work, statuses = []) {
	return statuses
		.map((status) => ({
			key: status,
			label: __(status),
			items: work.filter((task) => task.status === status),
			defaults: { status },
			can_add: !SYSTEM_STATUSES.includes(status) && status !== "Cancelled",
		}))
		.filter((group) => group.items.length || ALWAYS_SHOWN.includes(group.key));
}

/** Tasks under a top-level parent, however deep, that count towards its progress. */
const tasks_under = (phase, tasks) =>
	tasks.filter((task) => !task.is_group && task.top_parent === phase.name && task.status !== "Cancelled");

const by_plan = (a, b) =>
	(a.exp_start_date || "9999").localeCompare(b.exp_start_date || "9999") ||
	(a.exp_end_date || "9999").localeCompare(b.exp_end_date || "9999") ||
	String(a.creation).localeCompare(String(b.creation));

/**
 * One group per top-level parent task, in plan order, then the tasks with no parent the user can
 * read. While searching, parents with no matching task are left out.
 */
export function parent_groups(tasks, work, searching) {
	const groups = tasks
		.filter((task) => task.is_group && !task.parent_task)
		.sort(by_plan)
		.map((phase) => {
			const under = tasks_under(phase, tasks);
			return {
				key: phase.name,
				label: phase.subject || phase.name,
				phase,
				items: work.filter((task) => task.top_parent === phase.name),
				done: under.filter((task) => task.status === "Completed").length,
				total: under.length,
				people: [
					...new Set(
						under.filter((task) => !is_done(task)).flatMap((task) => task.assigned_to || [])
					),
				],
				defaults: { parent_task: phase.name },
				can_add: true,
			};
		})
		.filter((group) => group.items.length || !searching);
	const loose = work.filter((task) => !task.top_parent);
	if (loose.length) {
		groups.push({
			key: "",
			label: __("No parent task"),
			phase: null,
			items: loose,
			defaults: {},
			can_add: true,
		});
	}
	return groups;
}

/** Parent tasks whose tasks are all finished start folded. */
export const finished_phases = (groups) =>
	groups
		.filter((group) => group.phase && group.total && group.done === group.total)
		.map((group) => group.key);
