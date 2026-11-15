import { inject, provide } from "vue";

const ACTIONS = Symbol("overview-actions");

export const OPEN_TASK_STATUS = ["not in", ["Completed", "Cancelled", "Template"]];

export function createActions(element, host, project) {
	const send = (name, detail) =>
		element.value?.dispatchEvent(new CustomEvent(name, { bubbles: true, composed: true, detail }));
	const open_list = (doctype, filters) => send("overview-open-list", { doctype, filters });

	return {
		open_list,
		open_task_list: (filters = {}) =>
			open_list("Task", { project: project(), status: OPEN_TASK_STATUS, ...filters }),
		open_task: (name) => host.navigate?.(`Form/Task/${encodeURIComponent(name)}`),
		task_link: (name) =>
			window.frappe?.utils?.get_form_link?.("Task", name) || `/desk/task/${encodeURIComponent(name)}`,
		open_tab: (fieldname) => send("overview-open-tab", { fieldname }),
		new_task: () => send("overview-new-task"),
	};
}

export function person(user) {
	const { fullname, image } = window.frappe?.user_info?.(user) || {};
	return { user, fullname: fullname || user, image: image || undefined };
}

export const provideActions = (actions) => provide(ACTIONS, actions);
export const useActions = () => inject(ACTIONS);
