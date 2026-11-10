// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt
const BUDGETS = "erpnext.projects.doctype.project.costing.project_budgets";

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
		// the Costing tab asks for these dialogs with events, from inside its island
		$(frm.wrapper).on("costing-add-budget", (event) =>
			frm.events.add_project_budget(frm, event.originalEvent.detail)
		);
		$(frm.wrapper).on("costing-set-estimate", () => frm.events.set_estimate(frm));
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
		// Budget records are an Accounts Manager's; without them the Budgets tab hides
		frm.toggle_display("budgets_html", frappe.model.can_read("Budget"));
		frm.trigger("render_budgets");

		// the costing dashboard shows these totals; they stay in the meta for reports and list views
		frm.toggle_display(
			[
				"total_costing_amount",
				"total_purchase_cost",
				"total_sales_amount",
				"total_billable_amount",
				"total_billed_amount",
				"total_consumed_material_cost",
				"margin",
			],
			false
		);

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
				on_row_click: (row) => frm.events.open_task(frm, row.name),
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
			// the project is this one, so its field is only noise here
			const hide_project = (dialog) =>
				dialog instanceof frappe.ui.Dialog && dialog.set_df_property("project", "hidden", 1);
			frappe.ui.form.make_quick_entry("Task", () => frm.reload_doc(), hide_project, task);
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

	// A task opened from the Tasks tab, read and updated without leaving the project
	open_task: function (frm, name) {
		// loaded as the form loads it, so the permissions come resolved for this task: If owner,
		// user permissions and shares included
		frappe
			.call({
				method: "frappe.desk.form.load.getdoc",
				type: "GET",
				args: { doctype: "Task", name },
			})
			.then(({ docs: [task] }) => {
				// the dialog only edits, so a task the user may not change opens read only in its form
				if (!frappe.perm.has_perm("Task", 0, "write", task)) {
					frappe.set_route("Form", "Task", name);
					return;
				}
				// getdoc leaves out `_assign`; its docinfo has the open assignments, which the dialog changes
				const assigned = (frappe.model.get_docinfo("Task", name)?.assignments || []).map(
					(row) => row.owner
				);
				// Overdue and Template are set by the system, so only the task's own one of them is offered
				const statuses = frappe.meta
					.get_docfield("Task", "status")
					.options.split("\n")
					.filter((value) => !["Overdue", "Template"].includes(value) || value === task.status);
				const dialog = new frappe.ui.Dialog({
					title: task.name,
					size: "large",
					fields: [
						{ fieldname: "subject", fieldtype: "Data", label: __("Subject"), reqd: 1 },
						{ fieldtype: "Section Break", hide_border: 1 },
						{
							fieldname: "status",
							fieldtype: "Select",
							label: __("Status"),
							options: statuses.map((value) => ({ label: __(value), value })),
						},
						{ fieldtype: "Column Break" },
						{
							fieldname: "priority",
							fieldtype: "Select",
							label: __("Priority"),
							options: frappe.meta.get_docfield("Task", "priority").options,
						},
						{ fieldtype: "Section Break", hide_border: 1 },
						{
							fieldname: "assigned_to",
							fieldtype: "MultiSelectPills",
							label: __("Assigned to"),
							get_data: (txt) =>
								frappe.db.get_link_options("User", txt, {
									user_type: "System User",
									enabled: 1,
								}),
						},
						{ fieldtype: "Section Break", hide_border: 1 },
						{
							fieldname: "exp_start_date",
							fieldtype: "Datetime",
							label: __("Expected start"),
							description: task.act_start_date
								? __("Started {0}", [frappe.datetime.str_to_user(task.act_start_date)])
								: "",
						},
						{ fieldtype: "Column Break" },
						{ fieldname: "exp_end_date", fieldtype: "Datetime", label: __("Expected end") },
						{ fieldtype: "Column Break" },
						{
							fieldname: "expected_time",
							fieldtype: "Float",
							label: __("Expected hours"),
							description: flt(task.actual_time)
								? __("{0} h logged", [flt(task.actual_time, 2)])
								: "",
						},
						{ fieldtype: "Section Break", hide_border: 1 },
						{ fieldname: "description", fieldtype: "Text Editor", label: __("Description") },
					],
					primary_action_label: __("Save"),
					primary_action: ({ assigned_to, ...values }) => {
						const save = () =>
							frm.events
								.save_task(
									frm,
									task,
									values,
									dialog.shown_values,
									assigned,
									assigned_to || []
								)
								.then(() => {
									dialog.hide();
									frappe.show_alert({ message: __("Task updated"), indicator: "green" });
								});
						if (values.status === "Cancelled" && task.status !== "Cancelled") {
							frappe.confirm(
								__("Cancel task {0}?", [frappe.utils.escape_html(task.subject)]),
								save
							);
						} else {
							save();
						}
					},
					secondary_action_label: __("Open full form"),
					secondary_action: () => {
						dialog.hide();
						frappe.set_route("Form", "Task", task.name);
					},
				});
				dialog
					.set_values({
						subject: task.subject,
						status: task.status,
						priority: task.priority,
						assigned_to: assigned,
						exp_start_date: task.exp_start_date,
						exp_end_date: task.exp_end_date,
						expected_time: task.expected_time,
						description: task.description,
					})
					.then(() => {
						// each control shows a value in its own form, so edits are measured against these
						const { assigned_to, ...shown } = dialog.get_values(true);
						dialog.shown_values = shown;
					});
				dialog.show();
			});
	},

	// Only the fields changed in the dialog are saved, on the task as it was opened, so a change made
	// meanwhile is refused rather than overwritten. Assignments are added and removed for the
	// difference only.
	save_task: function (frm, task, values, shown, assigned, assigned_to) {
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
		return saved
			.then(async () => {
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
			})
			.then(() => {
				frm.tasks_list?.then((list) => list && frm.events.reload_task_rows(list));
				frm.events.refresh_project_progress(frm);
			});
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

	render_budgets: function (frm) {
		if (frm.is_new() || !frappe.model.can_read("Budget")) return;
		const STATUS_THEMES = { Active: "green", Draft: "orange", Cancelled: "gray" };
		frappe.require("embedded_list.bundle.js").then(() => {
			let budgets = {};
			const list = new frappe.ui.EmbeddedList({
				wrapper: frm.fields_dict.budgets_html.$wrapper.empty(),
				empty_message: __("No budgets for this project"),
				show_search: false,
				get_data: () =>
					frappe
						.xcall(`${BUDGETS}.get_project_budgets`, { project: frm.doc.name }, "GET")
						.then((response) => {
							budgets = response;
							return response.budgets;
						}),
				// a budget is cancelled or revised from its own form
				on_row_click: (row) => frappe.set_route("Form", "Budget", row.name),
				// the dialog submits the budget it creates
				add_button: frappe.model.can_create("Budget") &&
					frappe.model.can_submit("Budget") && {
						label: __("Add budget"),
						action: () =>
							frm.events.add_project_budget(frm, {
								budgeted: budgets.budgets
									.filter((row) => row.status === "Active")
									.map((row) => row.account),
							}),
					},
				columns: [
					{ label: __("Account"), render: (row) => frappe.utils.escape_html(row.account_name) },
					{ label: __("Budget"), render: (row) => frappe.utils.escape_html(row.name) },
					{
						label: __("Status"),
						render: (row) =>
							frappe.ui.badge.html({ label: __(row.status), theme: STATUS_THEMES[row.status] }),
					},
					{
						label: __("Amount"),
						align: "right",
						render: (row) => format_currency(row.amount, budgets.currency),
					},
					{
						label: __("Fiscal year"),
						render: (row) =>
							frappe.utils.escape_html(
								row.from_fiscal_year === row.to_fiscal_year
									? row.from_fiscal_year
									: `${row.from_fiscal_year} – ${row.to_fiscal_year}`
							),
					},
					{ label: __("Distribution frequency"), render: (row) => __(row.split) },
					{ label: __("When over"), render: (row) => frappe.utils.escape_html(row.rule) },
				],
			});
			list.refresh();
		});
	},

	set_estimate: function (frm) {
		const dialog = new frappe.ui.Dialog({
			title: __("Set estimate"),
			fields: [
				{
					fieldname: "estimated_costing",
					fieldtype: "Currency",
					label: __("Estimated cost"),
					reqd: 1,
				},
			],
			primary_action_label: __("Save"),
			primary_action: ({ estimated_costing }) => {
				if (estimated_costing <= 0) {
					frappe.msgprint(__("Enter an amount above zero."));
					return;
				}
				dialog.hide();
				frm.set_value("estimated_costing", estimated_costing).then(() => frm.save());
			},
		});
		dialog.show();
	},

	// The budget's fiscal years follow the project's expected dates, so they're read before the dialog opens
	add_project_budget: function (frm, { account = null, budgeted, on_saved }) {
		frappe
			.xcall(`${BUDGETS}.get_budget_defaults`, { project: frm.doc.name }, "GET")
			.then((years) => frm.events.budget_dialog(frm, { account, budgeted, on_saved, years }));
	},

	budget_dialog: function (frm, { account, budgeted, on_saved, years }) {
		const dialog = new frappe.ui.Dialog({
			title: __("Add budget"),
			size: "large",
			fields: [
				{
					fieldname: "account",
					fieldtype: "Link",
					options: "Account",
					label: __("Account"),
					reqd: 1,
					default: account,
					get_query: () => ({
						filters: [
							["company", "=", frm.doc.company],
							["root_type", "=", "Expense"],
							["is_group", "=", 0],
							["disabled", "=", 0],
							["name", "not in", budgeted || []],
						],
					}),
				},
				{
					fieldname: "amount",
					fieldtype: "Currency",
					label: __("Amount"),
					reqd: 1,
					onchange: () => fill_periods(),
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "split",
					fieldtype: "Select",
					label: __("Distribution frequency"),
					options: ["Monthly", "Quarterly", "Half-Yearly", "Yearly"],
					default: "Monthly",
					onchange: () => load_periods(),
				},
				{
					fieldname: "distribute_equally",
					fieldtype: "Check",
					label: __("Distribute equally"),
					default: 1,
					depends_on: "eval:doc.amount",
					onchange: () => fill_periods(),
				},
				{ fieldtype: "Section Break", hide_border: 1 },
				{
					fieldname: "from_fiscal_year",
					fieldtype: "Select",
					label: __("From fiscal year"),
					options: years.fiscal_years,
					default: years.from_fiscal_year,
					onchange: () => load_periods(),
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "to_fiscal_year",
					fieldtype: "Select",
					label: __("To fiscal year"),
					options: years.fiscal_years,
					default: years.to_fiscal_year,
					onchange: () => load_periods(),
				},
				{ fieldtype: "Section Break", depends_on: "eval:doc.amount && !doc.distribute_equally" },
				{
					fieldname: "periods",
					fieldtype: "Table",
					label: __("Amount per period"),
					cannot_add_rows: true,
					cannot_delete_rows: true,
					in_place_edit: true,
					depends_on: "eval:doc.amount && !doc.distribute_equally",
					data: [],
					fields: [
						{
							fieldname: "period",
							fieldtype: "Data",
							label: __("Period"),
							read_only: 1,
							in_list_view: 1,
						},
						{ fieldname: "amount", fieldtype: "Currency", label: __("Amount"), in_list_view: 1 },
					],
				},
				{ fieldtype: "Section Break" },
				{
					fieldname: "action",
					fieldtype: "Select",
					label: __("When spending goes over"),
					options: [
						{ label: __("Stop it"), value: "Stop" },
						{ label: __("Warn"), value: "Warn" },
						{ label: __("Track only"), value: "Ignore" },
					],
					default: "Stop",
				},
				{ fieldtype: "Column Break" },
				{
					fieldname: "check_from",
					fieldtype: "Select",
					label: __("Check from"),
					options: [
						{ label: __("Purchase order"), value: "Purchase Order" },
						{ label: __("Material request"), value: "Material Request" },
						{ label: __("Booking the expense"), value: "Expense" },
					],
					default: "Purchase Order",
					depends_on: "eval:doc.action != 'Ignore'",
				},
			],
			primary_action_label: __("Add budget"),
			primary_action(values) {
				const { periods, distribute_equally, ...budget } = values;
				if (!distribute_equally) {
					const total = (periods || []).reduce((sum, row) => sum + flt(row.amount), 0);
					if (Math.abs(total - flt(budget.amount)) > 0.01) {
						frappe.msgprint(
							__("The periods add up to {0}, but the budget is {1}", [
								format_currency(total),
								format_currency(budget.amount),
							])
						);
						return;
					}
					budget.period_amounts = periods.map((row) => flt(row.amount));
				}
				frappe
					.xcall(`${BUDGETS}.create_project_budget`, { project: frm.doc.name, ...budget })
					.then(() => {
						dialog.hide();
						frappe.show_alert({ message: __("Budget added"), indicator: "green" });
						on_saved?.();
						frm.trigger("render_budgets");
					});
			},
			secondary_action_label: __("Open full form"),
			secondary_action() {
				dialog.hide();
				frappe.new_doc("Budget", {
					budget_against: "Project",
					project: frm.doc.name,
					company: frm.doc.company,
					account: dialog.get_value("account"),
				});
			},
		});
		dialog.fields_dict.periods.$wrapper.addClass("budget-periods");

		let periods = [];
		// The periods come from ERPNext's own split of the chosen years
		function load_periods() {
			const args = {
				project: frm.doc.name,
				split: dialog.get_value("split"),
				from_fiscal_year: dialog.get_value("from_fiscal_year"),
				to_fiscal_year: dialog.get_value("to_fiscal_year"),
			};
			show_years_note();
			return frappe.xcall(`${BUDGETS}.get_budget_periods`, args, "GET").then((rows) => {
				periods = rows;
				fill_periods();
			});
		}

		// The project's own periods share the amount evenly; the last takes what rounding leaves
		function fill_periods() {
			if (dialog.get_value("distribute_equally")) return;
			const amount = flt(dialog.get_value("amount"));
			const shared = periods.some((p) => p.in_project) ? periods.filter((p) => p.in_project) : periods;
			const share = flt(amount / (shared.length || 1), 2);
			const last = shared[shared.length - 1];
			const field = dialog.fields_dict.periods;
			field.df.data = periods.map((p) => ({
				period: period_label(p.start_date, p.end_date),
				amount: !shared.includes(p)
					? 0
					: p === last
					? flt(amount - share * (shared.length - 1), 2)
					: share,
			}));
			field.grid.refresh();
		}

		function show_years_note() {
			const several = dialog.get_value("from_fiscal_year") !== dialog.get_value("to_fiscal_year");
			const notes = [
				years.capped && __("The project runs past the last fiscal year set up"),
				several && __("One amount for all these years"),
			].filter(Boolean);
			dialog.set_df_property("to_fiscal_year", "description", notes.join(". "));
		}

		load_periods();
		dialog.show();
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

// "Apr 2026" for one month, "Apr – Jun 2026" for several in one year.
function period_label(start_date, end_date) {
	const start = moment(start_date);
	const end = moment(end_date);
	if (start.isSame(end, "month")) return start.format("MMM YYYY");
	if (start.isSame(end, "year")) return `${start.format("MMM")} – ${end.format("MMM YYYY")}`;
	return `${start.format("MMM YYYY")} – ${end.format("MMM YYYY")}`;
}

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
