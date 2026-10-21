// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
frappe.ui.form.on("Project", {
	setup(frm) {
		frm.make_methods = {
			Timesheet: () => {
				open_form(frm, "Timesheet", "Timesheet Detail", "time_logs");
			},
			"Purchase Order": () => {
				open_form(frm, "Purchase Order", "Purchase Order Item", "items");
			},
			"Purchase Receipt": () => {
				open_form(frm, "Purchase Receipt", "Purchase Receipt Item", "items");
			},
			"Purchase Invoice": () => {
				open_form(frm, "Purchase Invoice", "Purchase Invoice Item", "items");
			},
		};
	},
	onload: function (frm) {
		const so = frm.get_docfield("sales_order");
		so.get_route_options_for_new_doc = () => {
			if (frm.is_new()) return {};
			return {
				customer: frm.doc.customer,
				project_name: frm.doc.name,
			};
		};

		frm.set_query("user", "users", function () {
			return {
				query: "erpnext.projects.doctype.project.project.get_users_for_project",
			};
		});

		frm.set_query("department", function (doc) {
			return {
				filters: {
					company: doc.company,
				},
			};
		});

		// sales order
		frm.set_query("sales_order", function () {
			var filters = {
				project: ["in", frm.doc.__islocal ? [""] : [frm.doc.name, ""]],
				company: frm.doc.company,
			};

			if (frm.doc.customer) {
				filters["customer"] = frm.doc.customer;
			}

			return {
				filters: filters,
			};
		});

		frm.set_query("cost_center", () => {
			return {
				filters: {
					company: frm.doc.company,
				},
			};
		});

		frm.set_query("customer", () => {
			return {
				filters: {
					disabled: 0,
				},
			};
		});

		frm.set_query("project_template", () => {
			return {
				filters: {
					disabled: 0,
				},
			};
		});
	},

	refresh: function (frm) {
		frm.web_link && frm.web_link.closest(".user-action-row").remove();

		if (!frm.doc.__islocal) {
			frm.add_web_link("/projects?project=" + encodeURIComponent(frm.doc.name));
		}
		frm.trigger("set_custom_buttons");

		// the Tasks tab holds only this field, so hiding it hides the tab, as for the Gantt and Kanban views
		frm.toggle_display("tasks_html", frappe.model.can_read("Task"));

		// the Tasks list is (re)built only once its tab is shown for this document
		frm.tasks_list = null;
		frm.trigger("load_tasks_tab");
	},

	on_tab_change: function (frm) {
		frm.trigger("load_tasks_tab");
	},

	load_tasks_tab: function (frm) {
		const active_tab = frm.get_active_tab && frm.get_active_tab();
		if (active_tab?.df?.fieldname !== "tasks_tab" || !frappe.model.can_read("Task")) return;

		if (frm.tasks_list) {
			// reload on every visit so tasks changed elsewhere show up
			frm.tasks_list.then((list) => list && list.refresh());
		} else {
			frm.tasks_list = frm.events.render_tasks(frm);
		}
	},

	render_tasks: function (frm) {
		const $wrapper = frm.get_field("tasks_html").$wrapper.empty();
		if (frm.is_new()) {
			$wrapper.html(
				`<p class="text-muted">${__("Save the Project first to add and view its Tasks.")}</p>`
			);
			return Promise.resolve();
		}

		const project = frm.doc.name;
		frm.tasks_sort ??= { sort_by: "creation", sort_order: "asc" };
		// loading Task's meta also loads task_list.js, whose indicators the Status column reuses
		const pending = Promise.all([
			frappe.require("embedded_list.bundle.js"),
			frappe.model.with_doctype("Task"),
		]).then(() => {
			// a refresh while loading starts over with a list of its own
			if (frm.tasks_list !== pending) return;

			const can_edit = frappe.model.can_write("Task");
			const editable = (field, html) => (can_edit ? frm.events.inline_edit_html(field, html) : html);
			const list = new frappe.ui.EmbeddedList({
				wrapper: $wrapper,
				get_page: ({ start, page_length, txt }) =>
					frappe.xcall("erpnext.projects.doctype.project.project.get_project_tasks", {
						project,
						...frm.tasks_sort,
						start,
						page_length,
						txt,
					}),
				empty_message: __("No Tasks in this Project yet."),
				add_button: frappe.model.can_create("Task") && {
					label: __("Add Task"),
					action: () => frm.events.create_task(frm),
				},
				on_row_click: (row) => frappe.set_route("Form", "Task", row.name),
				columns: [
					{ label: __("Task Name"), fieldname: "subject" },
					{
						label: __("Status"),
						fieldname: "status",
						render: (row) => {
							if (!row.status) return "";
							// the Task list gives no colour for statuses missing from its map, e.g. ones
							// added through Customize Form
							const [label, color] = frappe.get_indicator(row, "Task") || [];
							const badge = frappe.ui.badge.html({
								label: label || __(row.status),
								// badge knows "darkgrey" but not the list view's "dark grey"
								theme: (color || "gray").replace(" ", ""),
							});
							return editable("status", badge);
						},
					},
					{
						label: __("Priority"),
						fieldname: "priority",
						render: (row) => editable("priority", erpnext.utils.task_priority_html(row.priority)),
					},
					{
						label: __("Start Date"),
						fieldname: "exp_start_date",
						render: (row) => frappe.datetime.str_to_user(row.exp_start_date, false, true),
					},
					{
						label: __("End Date"),
						fieldname: "exp_end_date",
						render: (row) => frappe.datetime.str_to_user(row.exp_end_date, false, true),
					},
					{
						label: __("Progress"),
						fieldname: "progress",
						align: "right",
						render: (row) => frappe.format(flt(row.progress), { fieldtype: "Percent" }),
					},
					{
						label: __("Assigned To"),
						render: (row) =>
							frappe.ui.avatar_group.html({
								avatars: JSON.parse(row._assign || "[]").map((user) => {
									const { fullname, image } = frappe.user_info(user);
									return { label: fullname, image };
								}),
								max: 3,
								size: "sm",
								add: { title: __("Assign") },
							}),
					},
				],
			});

			const $actions = $wrapper.find(".embedded-list-header-actions");
			new frappe.ui.SortSelector({
				parent: $actions,
				doctype: "Task",
				args: {
					sort_by: frm.tasks_sort.sort_by,
					sort_order: frm.tasks_sort.sort_order,
					options: [
						{ fieldname: "creation", label: __("Created On") },
						{ fieldname: "modified", label: __("Last Updated On") },
						...list.columns
							.filter((column) => column.fieldname)
							.map(({ fieldname, label }) => ({ fieldname, label })),
					],
				},
				onchange: (sort_by, sort_order) => {
					frm.tasks_sort = { sort_by, sort_order };
					list.refresh();
				},
			}).wrapper.insertAfter($actions.find("[data-action='search']"));

			$wrapper.off(".project_tasks").on("click.project_tasks", ".task-inline-edit", (e) => {
				e.stopPropagation();
				const button = e.currentTarget;
				if ($(button).data("dropdown")) return;

				const row = list.data[$(button).closest("tr").attr("data-row-idx")];
				const field = button.dataset.field;
				const dropdown = new frappe.ui.Dropdown({
					trigger: button,
					options: () =>
						frm.events.task_field_options(frm, row, field, () =>
							frm.events.reload_task_rows(list)
						),
				});
				$(button).data("dropdown", dropdown);
				dropdown.open();
			});

			// cells are HTML, so the group's add button has no handler of its own
			$wrapper.on("click.project_tasks", ".es-avatar-group", (e) => {
				// the avatars only show their user's name on hover, rather than opening the task
				e.stopPropagation();
				if (!$(e.target).closest(".es-avatar-group__add").length) return;

				const row = list.data[$(e.currentTarget).closest("tr").attr("data-row-idx")];
				frm.events.assign_task(frm, row, () => frm.events.reload_task_rows(list));
			});

			list.refresh();
			return list;
		});
		return pending;
	},

	inline_edit_html: function (field, html) {
		const caret = frappe.utils.icon("chevron-down", "xs", "", "", "ml-1 text-ink-gray-4", true);
		return `<button type="button" class="btn-reset inline-flex items-center rounded task-inline-edit"
			data-field="${field}" title="${__("Change")}">${html}${caret}</button>`;
	},

	// Overdue and Template are set by the system, so they aren't offered
	task_field_options: function (frm, task, field, after) {
		const options = frappe.meta.get_docfield("Task", field).options.split("\n");
		const choices =
			field === "status"
				? options.filter((value) => !["Overdue", "Template"].includes(value))
				: options.slice().reverse();
		const icons = ["Urgent", "High", "Medium", "Low"];
		return choices.map((value) => ({
			label: __(value),
			icon: field === "priority" && icons.includes(value) ? `priority-${value.toLowerCase()}` : null,
			selected: task[field] === value,
			onclick: () => task[field] !== value && frm.events.update_task(frm, task, field, value, after),
		}));
	},

	update_task: function (frm, task, field, value, after) {
		const save = () =>
			frappe.db.set_value("Task", task.name, field, value).then(() => {
				after();
				frm.events.refresh_project_progress(frm);
			});
		if (field === "status" && value === "Cancelled") {
			frappe.confirm(__("Cancel task {0}?", [frappe.utils.escape_html(task.subject)]), save);
		} else {
			save();
		}
	},

	// EmbeddedList can't reload what it has loaded, so the page is widened for one request; reloads are
	// queued because they share that page size. Load More waits, as it would read the next page in the
	// new order while the rows shown are still in the old one; the redraw brings the button back
	reload_task_rows: function (list) {
		const disable_load_more = () =>
			list.$wrapper.find("[data-action='load-more']").prop("disabled", true);
		const reload = () => {
			disable_load_more();
			const page_size = list.page_size;
			list.page_size = Math.max(page_size, list.data.length);
			return list.load_page(0).finally(() => (list.page_size = page_size));
		};
		disable_load_more();
		const previous = list.task_reload || Promise.resolve();
		list.task_reload = previous.then(reload, reload);
		return list.task_reload;
	},

	// a task save leaves the project's modified as it was, so it isn't read back and the conflict check holds
	refresh_project_progress: function (frm) {
		const fields = ["percent_complete", "status"];
		const project = frm.doc.name;
		return frappe.db.get_value("Project", project, fields).then(({ message }) => {
			// the form is reused for the next Project opened, so a late reply may belong to another one
			if (frm.doc.name !== project) return;
			if (!frm.is_dirty()) {
				Object.assign(frm.doc, message);
				frm.refresh_fields(fields);
				frm.refresh_header();
			}
			frm.project_overview?.refresh();
		});
	},

	create_task: function (frm) {
		frappe.model.with_doctype("Task", () => {
			const task = frappe.model.get_new_doc("Task");
			task.project = frm.doc.name;
			frappe.ui.form.make_quick_entry("Task", () => frm.reload_doc(), null, task);
		});
	},

	set_custom_buttons: function (frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(
				__("Duplicate Project with Tasks"),
				() => {
					frm.events.create_duplicate(frm);
				},
				__("Actions")
			);

			frm.add_custom_button(
				__("Update Costing and Billing"),
				() => {
					frm.events.update_costing_and_billing(frm);
				},
				__("Actions")
			);

			frm.trigger("set_project_status_button");

			if (frappe.model.can_read("Task")) {
				frm.add_custom_button(
					__("Gantt Chart"),
					function () {
						frappe.route_options = {
							project: frm.doc.name,
						};
						frappe.set_route("List", "Task", "Gantt");
					},
					__("View")
				);

				frm.add_custom_button(
					__("Kanban Board"),
					() => {
						frappe
							.call(
								"erpnext.projects.doctype.project.project.create_kanban_board_if_not_exists",
								{
									project: frm.doc.name,
								}
							)
							.then((r) => {
								frappe.set_route("List", "Task", "Kanban", r.message);
							});
					},
					__("View")
				);
			}
		}
	},

	assign_task: function (frm, task, after_assign) {
		const assign_to = new frappe.ui.form.AssignToDialog({
			method: "frappe.desk.form.assign_to.add",
			doctype: "Task",
			docname: task.name,
			callback: after_assign,
		});
		// set from the form when assigning from a document; here there is only the row
		assign_to.dialog.set_value("description", task.subject);
		assign_to.dialog.show();
	},

	update_costing_and_billing: function (frm) {
		frappe.call({
			method: "erpnext.projects.doctype.project.project.update_costing_and_billing",
			args: { project: frm.doc.name },
			freeze: true,
			freeze_message: __("Updating Costing and Billing fields against this Project..."),
			callback: function (r) {
				if (r && !r.exc) {
					frappe.msgprint(__("Costing and Billing fields have been updated"));
					frm.refresh();
				}
			},
		});
	},

	set_project_status_button: function (frm) {
		frm.add_custom_button(
			__("Set Project Status"),
			() => frm.events.get_project_status_dialog(frm).show(),
			__("Actions")
		);
	},

	get_project_status_dialog: function (frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("Set Project Status"),
			fields: [
				{
					fieldname: "status",
					fieldtype: "Select",
					label: "Status",
					reqd: 1,
					options: "Completed\nCancelled",
				},
			],
			primary_action: function (values) {
				frm.events.set_status(frm, values.status);
				dialog.hide();
			},
			primary_action_label: __("Set Project Status"),
		});
		return dialog;
	},

	create_duplicate: function (frm) {
		frappe.prompt(
			{ fieldname: "project_name", fieldtype: "Data", label: __("Project Name"), reqd: 1 },
			(values) => {
				frappe
					.xcall("erpnext.projects.doctype.project.project.create_duplicate_project", {
						prev_doc: frm.doc,
						project_name: values.project_name,
					})
					// the new project is named by its naming series, so find it by its (unique) Project Name
					.then(() => frappe.db.get_value("Project", { project_name: values.project_name }, "name"))
					.then(({ message }) => {
						frappe.set_route("Form", "Project", message.name);
						frappe.show_alert(__("Duplicate project has been created"));
					});
			},
			__("Duplicate Project with Tasks"),
			__("Create")
		);
	},

	set_status: function (frm, status) {
		frappe.confirm(__("Set Project and all Tasks to status {0}?", [__(status).bold()]), () => {
			frappe
				.xcall("erpnext.projects.doctype.project.project.set_project_status", {
					project: frm.doc.name,
					status: status,
				})
				.then(() => {
					frm.reload_doc();
				});
		});
	},

	collect_progress: function (frm) {
		if (frm.doc.collect_progress && !frm.doc.subject) {
			frm.set_value("subject", __("For project - {0}, update your status", [frm.doc.project_name]));
		}
	},
});

function open_form(frm, doctype, child_doctype, parentfield) {
	frappe.model.with_doctype(doctype, () => {
		let new_doc = frappe.model.get_new_doc(doctype);

		// add a new row and set the project
		let new_child_doc = frappe.model.get_new_doc(child_doctype);
		new_child_doc.project = frm.doc.name;
		new_child_doc.parent = new_doc.name;
		new_child_doc.parentfield = parentfield;
		new_child_doc.parenttype = doctype;
		new_doc[parentfield] = [new_child_doc];
		new_doc.project = frm.doc.name;
		if (frm.doc.company) {
			new_doc.company = frm.doc.company;
		}

		frappe.ui.form.make_quick_entry(doctype, null, null, new_doc);
	});
}
