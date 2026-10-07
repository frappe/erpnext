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
		// loading Task's meta also loads task_list.js, whose indicators the Status column reuses
		const pending = Promise.all([
			frappe.require("embedded_list.bundle.js"),
			frappe.model.with_doctype("Task"),
		]).then(() => {
			// a refresh while loading starts over with a list of its own
			if (frm.tasks_list !== pending) return;

			const list = new frappe.ui.EmbeddedList({
				wrapper: $wrapper,
				get_page: ({ start, page_length, txt }) => {
					const args = {
						fields: [
							"name",
							"subject",
							"status",
							"priority",
							"_assign",
							"exp_start_date",
							"exp_end_date",
							"progress",
						],
						filters: { project },
						order_by: "creation asc",
						start,
						limit: page_length,
					};
					if (txt) {
						args.or_filters = [
							["subject", "like", `%${txt}%`],
							["name", "like", `%${txt}%`],
						];
					}
					return frappe.db.get_list("Task", args);
				},
				empty_message: __("No Tasks in this Project yet."),
				add_button: frappe.model.can_create("Task") && {
					label: __("Add Task"),
					action: () => {
						frappe.model.with_doctype("Task", () => {
							const task = frappe.model.get_new_doc("Task");
							task.project = frm.doc.name;
							// % Complete and status are recomputed on the server when a task changes
							frappe.ui.form.make_quick_entry("Task", () => frm.reload_doc(), null, task);
						});
					},
				},
				on_row_click: (row) => frappe.set_route("Form", "Task", row.name),
				columns: [
					{ label: __("Task Name"), fieldname: "subject" },
					{
						label: __("Status"),
						render: (row) => {
							const [label, color] = frappe.get_indicator(row, "Task") || [
								__(row.status),
								"gray",
							];
							// badge knows "darkgrey" but not the list view's "dark grey"
							return frappe.ui.badge.html({ label, theme: color.replace(" ", "") });
						},
					},
					{ label: __("Priority"), render: (row) => __(row.priority || "") },
					{
						label: __("Start Date"),
						render: (row) => frappe.datetime.str_to_user(row.exp_start_date, false, true),
					},
					{
						label: __("End Date"),
						render: (row) => frappe.datetime.str_to_user(row.exp_end_date, false, true),
					},
					{
						label: __("Progress"),
						align: "right",
						render: (row) => frappe.format(flt(row.progress), { fieldtype: "Percent" }),
					},
					{
						label: __("Assigned To"),
						render: (row) =>
							frappe
								.avatar_group(JSON.parse(row._assign || "[]"), 3, {
									align: "left",
									overlap: true,
									action_icon: "plus",
								})
								.prop("outerHTML"),
					},
				],
			});

			// cells are rendered as HTML, so avatar_group's own handler for "+" is lost; bound here instead
			$wrapper.off(".project_tasks").on("click.project_tasks", ".avatar-group", (e) => {
				// the avatars only show their user's name on hover, rather than opening the task
				e.stopPropagation();
				if (!$(e.target).closest(".avatar-action").length) return;

				const row = list.data[$(e.currentTarget).closest("tr").attr("data-row-idx")];
				frm.events.assign_task(frm, row, () => list.refresh());
			});

			list.refresh();
			return list;
		});
		return pending;
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
							.then(() => {
								frappe.set_route("List", "Task", "Kanban", frm.doc.project_name);
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
			primary_action: function () {
				frm.events.set_status(frm, dialog.get_values().status);
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
