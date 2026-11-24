import { inject, provide, ref, watch } from "vue";

const TASKS = Symbol("project-tasks");

export const provideTasks = (context) => provide(TASKS, context);
export const useTasks = () => inject(TASKS);

/**
 * Edits shown before the server confirms them. The tasks come in as a prop that the form replaces
 * after each save, so an edit lives here, on top of them, until fresh tasks arrive. An edit still
 * being saved outlives a reload; one the server refuses is taken back.
 */
export function useTaskEdits(source, send) {
	const changes = ref({});
	const saving = new Map();

	watch(source, () => {
		changes.value = Object.fromEntries(
			Object.entries(changes.value).filter(([name]) => saving.get(name))
		);
	});

	const view = (task) => (changes.value[task.name] ? { ...task, ...changes.value[task.name] } : task);

	async function edit(task, values, write) {
		const before = changes.value[task.name];
		changes.value = { ...changes.value, [task.name]: { ...before, ...values } };
		saving.set(task.name, (saving.get(task.name) || 0) + 1);
		try {
			await write();
			send("tasks-changed", { name: task.name });
		} catch {
			const { [task.name]: _, ...rest } = changes.value;
			changes.value = before ? { ...rest, [task.name]: before } : rest;
		} finally {
			saving.set(task.name, saving.get(task.name) - 1);
		}
	}

	return { view, edit };
}
