// The task dialog: a title and a description, then the task's properties as a row of buttons.
// It is Task's quick entry wherever desk opens one (the Task list, "Create a new Task" from a Link
// field, a Kanban column's "+"), and how the Project form's Tasks tab creates and edits tasks.
// Where a site or a caller customised Task's quick entry, desk's own quick entry is kept.

frappe.provide("erpnext.tasks");

const CREATE_TASK = "erpnext.projects.doctype.project.project_tasks.create_task";
// the Task fields the dialog sets
const DIALOG_FIELDS = [
	"subject",
	"project",
	"status",
	"priority",
	"parent_task",
	"exp_start_date",
	"exp_end_date",
	"expected_time",
	"description",
];
const PRIORITY_ICONS = {
	Urgent: "circle-alert",
	High: "signal-high",
	Medium: "signal-medium",
	Low: "signal-low",
};

/**
 * Whether Task's quick entry is as it ships: switched on, and asking for no field this dialog
 * doesn't have. A site that made another field mandatory or added one to the quick entry keeps
 * desk's quick entry, which shows those fields. Task's meta must be loaded.
 */
erpnext.tasks.can_use_dialog = function () {
	const meta = frappe.get_meta("Task");
	if (!meta || cint(meta.quick_entry) !== 1) return false;
	return meta.fields
		.filter(
			(df) =>
				(df.reqd || df.allow_in_quick_entry) &&
				!df.read_only &&
				!df.is_virtual &&
				df.fieldtype !== "Tab Break"
		)
		.every((df) => DIALOG_FIELDS.includes(df.fieldname));
};

/**
 * Opens the task dialog.
 *
 * @param {Object} [opts.task] An existing task to edit; without it the dialog makes a new one.
 * @param {string[]} [opts.assigned] The edited task's open assignments.
 * @param {Object} [opts.doc] A new task's starting values, such as project, status and parent_task.
 * @param {boolean} [opts.fixed_project] The page gives the project, so the dialog doesn't ask.
 * @param {string[]} [opts.people] Users offered first in Assign to, such as the project's team.
 * @param {function} [opts.on_created] Called with the new task as saved.
 * @param {function} [opts.on_saved] Called after an edit is saved.
 * @param {function} [opts.on_full_form] New task only: shows "Edit full form", called with the values
 *   and the people picked in Assign to.
 */
erpnext.tasks.open_dialog = function ({
	task = null,
	assigned = [],
	doc = {},
	fixed_project = false,
	people = [],
	on_created,
	on_saved,
	on_full_form,
} = {}) {
	const is_new = !task;
	const label = (fieldname) => __(frappe.meta.get_label("Task", fieldname));
	// Overdue and Template are set by the system, so only the task's own one of them is offered;
	// a new task can't start cancelled
	const statuses = frappe.meta
		.get_docfield("Task", "status")
		.options.split("\n")
		.filter((value) =>
			is_new
				? !["Overdue", "Template", "Cancelled"].includes(value)
				: !["Overdue", "Template"].includes(value) || value === task.status
		);
	const priority_df = frappe.meta.get_docfield("Task", "priority");
	// what the buttons set; the dialog's own fields hold the title and the description
	const state = is_new
		? {
				project: doc.project || null,
				status: statuses.includes(doc.status) ? doc.status : "Open",
				// as desk starts a new task: the field's default, else its first option
				priority: doc.priority || priority_df.default || priority_df.options.split("\n")[0],
				parent_task: doc.parent_task || null,
				assigned_to: [],
				exp_start_date: doc.exp_start_date || null,
				exp_end_date: doc.exp_end_date || null,
		  }
		: {
				status: task.status,
				priority: task.priority,
				assigned_to: [...assigned],
				exp_start_date: task.exp_start_date,
				exp_end_date: task.exp_end_date,
				expected_time: task.expected_time,
		  };
	// what the page that opened the dialog filled in beyond the dialog's own fields, such as the
	// Issue a task is made from; a new task keeps it, as desk's quick entry does
	const carried = is_new
		? Object.fromEntries(
				Object.entries(doc).filter(
					([fieldname, value]) =>
						!fieldname.startsWith("__") &&
						fieldname !== "doctype" &&
						!frappe.model.std_fields_list.includes(fieldname) &&
						!DIALOG_FIELDS.includes(fieldname) &&
						!Array.isArray(value) &&
						!is_null(value)
				)
		  )
		: {};

	const dialog = new frappe.ui.Dialog({
		title: is_new ? __("New task") : task.name,
		size: "large",
		fields: [
			{ fieldname: "subject", fieldtype: "Data", label: label("subject"), reqd: 1 },
			{
				fieldname: "description",
				fieldtype: "Text Editor",
				label: label("description"),
				max_height: "16rem",
			},
			{ fieldname: "properties", fieldtype: "HTML" },
		],
		primary_action_label: is_new ? __("Create task") : __("Save"),
		primary_action: ({ subject, description }) => {
			const { assigned_to, ...properties } = state;
			const values = { subject, description, ...properties };
			if (is_new) {
				run(() => insert({ ...carried, ...values }, assigned_to));
				return;
			}
			const done = () =>
				save_task(task, values, dialog.shown_values, assigned, assigned_to).then(() => {
					dialog.hide();
					frappe.show_alert({ message: __("Task updated"), indicator: "green" });
					on_saved?.();
				});
			if (values.status === "Cancelled" && task.status !== "Cancelled") {
				// the confirmation counts as running, so a second ⌘↵ doesn't open another one
				run(
					() =>
						new Promise((resolve, reject) =>
							frappe.confirm(
								__("Cancel task {0}?", [frappe.utils.escape_html(task.subject)]),
								() => done().then(resolve, reject),
								resolve
							)
						)
				);
			} else {
				run(done);
			}
		},
		...(is_new
			? on_full_form && {
					secondary_action_label: __("Edit full form"),
					secondary_action: () => {
						dialog.hide();
						const { assigned_to, ...properties } = state;
						on_full_form({ ...dialog.get_values(true), ...properties }, assigned_to);
					},
			  }
			: {
					secondary_action_label: __("Open full form"),
					secondary_action: () => {
						dialog.hide();
						frappe.set_route("Form", "Task", task.name);
					},
			  }),
	});

	// One save at a time, as desk's quick entry does with `dialog.working`: ⌘↵ clicks the button
	// from code, which a disabled button doesn't stop, so two quick presses would save twice. On an
	// error the dialog stays open with what was typed, and desk has shown the server's message.
	function run(work) {
		if (dialog.working) return;
		dialog.working = true;
		const $button = dialog.get_primary_btn().prop("disabled", true);
		return Promise.resolve()
			.then(work)
			.catch(() => {})
			.finally(() => {
				dialog.working = false;
				$button.prop("disabled", false);
			});
	}

	// Creates the task and its assignments in one request
	function insert(values, assigned_to) {
		// an untouched Text Editor still returns an empty paragraph
		if (!strip_html(values.description || "").trim()) delete values.description;
		return frappe.xcall(CREATE_TASK, { task: values, assign_to: assigned_to }).then((created) => {
			dialog.hide();
			frappe.show_alert({ message: __("Task created"), indicator: "green" });
			on_created?.(created);
		});
	}

	make_properties(dialog, state, { statuses, priority_df, task, fixed_project, people, label });
	// a few lines to start with, as the description is often filled in later; it grows as you type
	dialog.get_field("description").$wrapper.find(".ql-editor").css({ height: "auto", "min-height": "6rem" });

	dialog
		.set_values({
			subject: task ? task.subject : doc.subject,
			description: task ? task.description : doc.description,
		})
		.then(() => {
			// each control shows a value in its own form, so edits are measured against these
			const { subject, description } = dialog.get_values(true);
			const { assigned_to, ...properties } = state;
			dialog.shown_values = { subject, description, ...properties };
		});

	// ⌘↵ (Ctrl+Enter) creates or saves, as the hint in the footer says
	const key = frappe.utils.is_mac() ? "⌘" : "Ctrl";
	$(`<span class="me-auto text-sm text-ink-gray-5 max-sm:hidden"></span>`)
		.append($("<kbd>").text(key), " ", $("<kbd>").text("↵"))
		.prependTo(dialog.$wrapper.find(".modal-footer"));
	dialog.$wrapper.on("keydown", (event) => {
		if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
			event.preventDefault();
			dialog.get_primary_btn().trigger("click");
		}
	});
	dialog.show();
	return dialog;
};

// The dialog's row of property buttons; each writes into `state`
function make_properties(dialog, state, { statuses, priority_df, task, fixed_project, people, label }) {
	const $field = dialog.get_field("properties").$wrapper.empty();
	const $row = $(`<div class="flex flex-wrap items-center gap-2"></div>`).appendTo($field);
	const slot = (width) =>
		$("<div></div>")
			.css(width ? { width } : {})
			.appendTo($row);
	// a new task asks for its project unless the page gives it
	const $project = !task && !fixed_project ? slot("14rem") : null;
	const $status = slot();
	const $priority = slot();
	const $assign = slot("14rem");
	const $parent = slot();
	const $dates = slot("14rem");
	const $hours = task ? slot("7rem") : null;

	// a new task can go under one of its project's parent tasks
	let parents = [];
	const load_parents = () => {
		parents = [];
		if (task || !state.project) return render();
		const project = state.project;
		frappe.db
			.get_list("Task", {
				filters: { project, is_group: 1 },
				fields: ["name", "subject"],
				order_by: "lft asc",
				limit: 0,
			})
			.then((rows) => {
				// the project changed while these were on their way
				if (project !== state.project) return;
				parents = rows;
				render();
			});
	};

	const menu = ($slot, button, options) => {
		const dropdown = new frappe.ui.Dropdown({
			button: { size: "sm", icon_right: "chevron-down", ...button },
			options,
		});
		$slot.empty().append(dropdown.$trigger);
	};
	const pick = (fieldname, value) => () => {
		state[fieldname] = value;
		render();
	};
	const parent_label = (name) => {
		const parent = parents.find((row) => row.name === name);
		return parent ? parent.subject || parent.name : name;
	};
	function render() {
		menu(
			$status,
			{ label: __(state.status), icon: "circle-dot" },
			statuses.map((value) => ({
				label: __(value),
				selected: value === state.status,
				onclick: pick("status", value),
			}))
		);
		menu(
			$priority,
			{
				label: state.priority ? __(state.priority) : label("priority"),
				icon: PRIORITY_ICONS[state.priority] || "signal",
			},
			priority_df.options
				.split("\n")
				.filter(Boolean)
				.reverse()
				.map((value) => ({
					label: __(value),
					icon: PRIORITY_ICONS[value],
					selected: value === state.priority,
					onclick: pick("priority", value),
				}))
		);
		// a new task only: an existing one changes its parent on its form
		const has_parent = !task && (parents.length || state.parent_task);
		// an empty slot would still take a gap in the row
		$parent.empty().toggle(Boolean(has_parent));
		if (has_parent) {
			menu(
				$parent,
				{
					label: state.parent_task ? parent_label(state.parent_task) : label("parent_task"),
					icon: "list-tree",
				},
				[
					...parents.map((parent) => ({
						label: parent.subject || parent.name,
						selected: parent.name === state.parent_task,
						onclick: pick("parent_task", parent.name),
					})),
					...(state.parent_task
						? [{ label: __("No parent task"), icon: "x", onclick: pick("parent_task", null) }]
						: []),
				]
			);
		}
	}
	render();
	load_parents();

	if ($project) {
		const project = new frappe.ui.Combobox({
			value: state.project,
			placeholder: label("project"),
			search_placeholder: __("Search projects"),
			filterable: false,
			options: (query) =>
				frappe.db.get_link_options("Project", query).then((rows) =>
					(rows || []).map((row) => ({
						value: row.value,
						label: row.label || row.value,
						description: row.description,
					}))
				),
			on_change: (value) => {
				state.project = value || null;
				state.parent_task = null;
				load_parents();
			},
		});
		$project.append(project.$trigger);
	}

	// before anything is typed: the people already given (assigned here, or on the project), then
	// other desk users; typing searches every desk user
	const person = (user, name) => {
		const { fullname, image } = frappe.user_info(user) || {};
		return { value: user, label: name || fullname || user, image, avatar: !image };
	};
	const search_users = (query) =>
		frappe.db
			.get_link_options("User", query, { user_type: "System User", enabled: 1 }, 20)
			.then((rows) => (rows || []).map((row) => person(row.value, row.label)));
	const suggestions = () =>
		search_users("").then((found) => {
			// the search knows names desk may not have loaded yet
			const names = Object.fromEntries(found.map((option) => [option.value, option.label]));
			const first = [...new Set([...state.assigned_to, ...people])];
			return [
				...first.map((user) => person(user, names[user])),
				...found.filter((option) => !first.includes(option.value)),
			];
		});
	const assign = new frappe.ui.MultiCombobox({
		value: state.assigned_to.map((user) => person(user)),
		placeholder: __("Assign to"),
		search_placeholder: __("Search people"),
		one_line: true,
		filterable: false,
		options: (query) => (query ? search_users(query) : suggestions()),
		on_change: (values) => (state.assigned_to = values),
	});
	$assign.append(assign.$trigger);

	// dates only: a time an existing task already has is kept unless the range is changed
	const day = (value) => (value ? String(value).slice(0, 10) : null);
	const dates = frappe.ui.form.make_control({
		df: {
			fieldtype: "DateRange",
			fieldname: "task_dates",
			placeholder: __("Expected start – end"),
			change: () => {
				const [start, end] = dates.get_value() || [];
				if (day(start) === day(state.exp_start_date) && day(end) === day(state.exp_end_date)) return;
				state.exp_start_date = start || null;
				state.exp_end_date = end || null;
			},
		},
		parent: $dates,
		only_input: true,
		render_input: true,
	});
	// a form control keeps a field's bottom margin, which would lift it off the row's centre line
	dates.$wrapper.css("margin-bottom", 0);
	if (state.exp_start_date && state.exp_end_date) {
		dates.set_value([day(state.exp_start_date), day(state.exp_end_date)]);
	}

	if ($hours) {
		const hours = frappe.ui.form.make_control({
			df: {
				fieldtype: "Float",
				fieldname: "task_hours",
				placeholder: __("Hours"),
				change: () => (state.expected_time = hours.get_value()),
			},
			parent: $hours,
			only_input: true,
			render_input: true,
		});
		hours.$wrapper.css("margin-bottom", 0);
		hours.set_value(state.expected_time);
		hours.$input.attr({ title: label("expected_time"), "aria-label": label("expected_time") });
	}

	// what already happened on the task, for context while planning it
	const notes = [
		task?.act_start_date && __("Started {0}", [frappe.datetime.str_to_user(task.act_start_date)]),
		flt(task?.actual_time) && __("{0} h logged", [flt(task.actual_time, 2)]),
	].filter(Boolean);
	if (notes.length) {
		$(`<div class="mt-2 text-sm text-ink-gray-5"></div>`).text(notes.join(" · ")).appendTo($field);
	}
}

// Only the fields changed in the dialog are saved, on the task as it was opened, so a change made
// meanwhile is refused rather than overwritten. Assignments are added and removed for the
// difference only.
function save_task(task, values, shown, assigned, assigned_to) {
	const add = assigned_to.filter((user) => !assigned.includes(user));
	const remove = assigned.filter((user) => !assigned_to.includes(user));
	// get_values leaves an empty field out, so a field cleared in the dialog is missing from `values`
	const fields = new Set([...Object.keys(shown), ...Object.keys(values)]);
	const changes = Object.fromEntries(
		[...fields]
			.map((field) => [field, values[field] ?? null])
			.filter(([field, value]) => !frappe.utils.deep_equal(value, shown[field] ?? null))
	);
	const saved = Object.keys(changes).length
		? frappe.xcall("frappe.client.save", { doc: { ...task, ...changes } })
		: Promise.resolve();
	return saved.then(async () => {
		// one at a time: each call rewrites the task's `_assign`, and calls in parallel deadlock on its row
		if (add.length) {
			await frappe.xcall("frappe.desk.form.assign_to.add", {
				doctype: "Task",
				name: task.name,
				assign_to: add,
				description: values.subject,
			});
		}
		for (const user of remove) {
			await frappe.xcall("frappe.desk.form.assign_to.remove", {
				doctype: "Task",
				name: task.name,
				assign_to: user,
			});
		}
	});
}

// What a new task opened in its full form from the dialog still needs once it is first saved: the
// people picked in Assign to, and the callback of the page that opened the dialog. Keyed by the
// new task's local name, which desk maps to its saved name. A form left unsaved never matches.
const after_first_save = {};

/**
 * "Edit full form" for a new task: opens `doc`, a new local Task, with the dialog's `values`.
 * A form can't hold assignments before its first save, so `assign_to` and `after_insert`, which
 * gets the saved task, wait for it.
 */
erpnext.tasks.open_new_in_full_form = function (doc, values, { assign_to = [], after_insert } = {}) {
	Object.entries(values).forEach(([fieldname, value]) => {
		if (!is_null(value)) doc[fieldname] = value;
	});
	if (assign_to.length || after_insert) {
		after_first_save[doc.name] = {
			assign_to,
			after_insert,
			// noted now: the save clears it when it fills the Link field, before the assignments
			// come back
			from_link: Boolean(frappe._from_link),
		};
	}
	doc.__run_link_triggers = false;
	frappe.set_route("Form", "Task", doc.name);
};

frappe.ui.form.on("Task", {
	after_save(frm) {
		const local = Object.keys(after_first_save).find(
			(name) => frappe.model.new_names[name] === frm.doc.name
		);
		if (!local) return;
		const { assign_to, after_insert, from_link } = after_first_save[local];
		delete after_first_save[local];
		// the Assign dialog's own endpoint, with its checks; desk shows why if it refuses someone
		const assigned = assign_to.length
			? frappe
					.xcall("frappe.desk.form.assign_to.add", {
						doctype: "Task",
						name: frm.doc.name,
						assign_to,
						description: frm.doc.subject,
					})
					.then(() => frm.reload_doc())
			: Promise.resolve();
		// as desk's quick entry: the opener's callback gets the saved task, except where a Link field
		// opened the dialog, as the save already filled that field
		assigned.catch(() => {}).finally(() => !from_link && after_insert?.(frm.doc));
	},
});

// Task's quick entry. Desk opens it for every new Task; it shows the task dialog unless desk's own
// quick entry is what the caller or the site expects. Another app's TaskQuickEntryForm, loaded
// after ERPNext, replaces this one.
if (!frappe.ui.form.TaskQuickEntryForm) {
	frappe.ui.form.TaskQuickEntryForm = class TaskQuickEntryForm extends frappe.ui.form.QuickEntryForm {
		setup() {
			return frappe.model.with_doctype(this.doctype).then(() => {
				this.check_quick_entry_doc();
				// desk's quick entry where it is what's expected: a caller adjusting it by init
				// callback, a caller wanting the values without an insert, an existing task, or a
				// site that customised Task's quick entry
				if (
					this.init_callback ||
					this.skip_insert ||
					!this.doc.__islocal ||
					!erpnext.tasks.can_use_dialog()
				) {
					return super.setup();
				}
				erpnext.tasks.open_dialog({
					doc: this.doc,
					on_created: (task) => this.created(task),
					on_full_form: (values, assign_to) => this.full_form(values, assign_to),
				});
				frappe.quick_entry = null;
				return this;
			});
		}

		// as desk's quick entry does after an insert: fill the Link field that asked for the task,
		// or run the caller's callback, or open the task
		created(task) {
			this.process_after_insert({ message: task });
			if (frappe.route_hooks.after_save) {
				const route_callback = frappe.route_hooks.after_save;
				delete frappe.route_hooks.after_save;
				route_callback(this);
			}
		}

		full_form(values, assign_to = []) {
			erpnext.tasks.open_new_in_full_form(this.doc, values, {
				assign_to,
				after_insert: this.after_insert,
			});
		}
	};
}
