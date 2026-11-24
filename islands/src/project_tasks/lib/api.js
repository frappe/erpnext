// Writes go through desk, which holds the CSRF token. A refused write shows desk's own error
// message, and the promise rejects so the tab can undo what it showed.
const desk = () => window.frappe;

export const set_task_value = (name, fieldname, value) =>
	desk().xcall("frappe.client.set_value", { doctype: "Task", name, fieldname, value });

// One at a time: each call rewrites the task's `_assign`, and calls in parallel deadlock on its row.
let assigning = Promise.resolve();

export function change_assignees(task, add, remove) {
	const run = async () => {
		if (add.length) {
			await desk().xcall("frappe.desk.form.assign_to.add", {
				doctype: "Task",
				name: task.name,
				assign_to: add,
				description: task.subject,
			});
		}
		for (const user of remove) {
			await desk().xcall("frappe.desk.form.assign_to.remove", {
				doctype: "Task",
				name: task.name,
				assign_to: user,
			});
		}
	};
	const result = assigning.catch(() => {}).then(run);
	assigning = result;
	return result;
}

// enabled desk users matching `text`, as the task dialog's Assigned to field finds them
export const search_users = (text) =>
	desk().db.get_link_options("User", text, { user_type: "System User", enabled: 1 }, 20);

export function confirm(message) {
	return new Promise((resolve) =>
		desk().confirm(
			message,
			() => resolve(true),
			() => resolve(false)
		)
	);
}
