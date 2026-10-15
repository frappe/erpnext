// The Overview tab's task donut and per-person list, side by side: open work while the project runs,
// and how it was delivered once it is completed or cancelled
erpnext.ProjectOverviewBreakdown = class ProjectOverviewBreakdown {
	constructor(overview) {
		this.overview = overview;
	}

	render(data) {
		const $row = $('<div class="po-section po-two-col">').appendTo(this.overview.$root);
		const panel = (title) => this.overview.panel($row, title);
		if (data.delivery) {
			this.render_delivery(panel(__("Tasks by Outcome")), data.tasks_by_delivery);
			this.render_completed(panel(__("Completed by Assignee")), data.completed_by_assignee);
		} else {
			this.render_status(panel(__("Tasks by Status")), data.tasks_by_status);
			this.render_workload(panel(__("Open Tasks by Assignee")), data.workload);
		}
	}

	render_delivery($panel, by_delivery) {
		if (!by_delivery) return this.error($panel);

		const colors = this.outcome_colors();
		this.donut($panel, {
			slices: by_delivery.outcomes.map(({ outcome, count }) => ({
				label: __(outcome),
				value: count,
				color: colors[outcome],
				onclick: () => this.open_outcome(outcome),
			})),
			total: by_delivery.total,
		});
	}

	render_completed($panel, completed) {
		if (!completed) return this.error($panel);

		const columns = [
			{ label: __("Assignee"), render: (row) => this.assignee_html(row.user) },
			{ label: __("Completed"), align: "right", render: (row) => this.completed_count_html(row) },
		];

		new frappe.ui.EmbeddedList({
			wrapper: $("<div>").appendTo($panel),
			get_data: () => Promise.resolve(completed.rows),
			columns,
			show_search: false,
			empty_icon: "users",
			empty_message: __("No completed tasks"),
			on_row_click: (row) => this.overview.open_list("Task", { name: ["in", row.tasks] }),
		}).refresh();
	}

	render_status($panel, by_status) {
		if (!by_status) return this.error($panel);

		const colors = this.status_colors();
		this.donut($panel, {
			slices: by_status.statuses.map(({ status, count }) => ({
				label: __(status),
				value: count,
				color: colors[status],
				onclick: () => this.open_status(status),
			})),
			total: by_status.total,
		});
	}

	// each slice opens the tasks behind it; slices stay in the order given, as there are far fewer
	// than frappe-charts' maxSlices
	donut($panel, { slices, total }) {
		frappe.utils.make_chart($('<div class="po-donut">').appendTo($panel)[0], {
			type: "donut",
			height: 280,
			colors: slices.map((slice) => slice.color),
			data: {
				labels: slices.map((slice) => slice.label),
				datasets: [{ values: slices.map((slice) => slice.value) }],
			},
			center: { value: format_number(total, null, 0), label: __("tasks") },
			onClick: ({ index }) => slices[index].onclick(),
		});
	}

	render_workload($panel, workload) {
		if (!workload) return this.error($panel);

		const columns = [
			{ label: __("Assignee"), render: (row) => this.assignee_html(row.user) },
			{ label: __("Open Tasks"), align: "right", render: (row) => this.open_count_html(row) },
		];

		new frappe.ui.EmbeddedList({
			wrapper: $("<div>").appendTo($panel),
			get_data: () => Promise.resolve(workload.rows),
			columns,
			show_search: false,
			empty_icon: "users",
			empty_message: __("No open tasks"),
			on_row_click: (row) => this.open_assignee_tasks(row.user),
		}).refresh();
	}

	assignee_html(user) {
		if (!user) return `<span class="text-ink-gray-5">${__("Unassigned")}</span>`;
		const { fullname, image } = frappe.user_info(user);
		const avatar = frappe.ui.avatar.html({ label: fullname, image, size: "sm" });
		return `<span class="po-assignee">${avatar}<span class="po-assignee-name">${frappe.utils.escape_html(
			fullname
		)}</span></span>`;
	}

	// the overdue part is mentioned only when there is one, so most rows read as just a number
	open_count_html({ open, overdue }) {
		const count = format_number(open, null, 0);
		if (!overdue) return count;
		const late = __("{0} overdue", [format_number(overdue, null, 0)]);
		return `${count} <span class="text-ink-gray-4">·</span> <span class="text-ink-red-7">${late}</span>`;
	}

	completed_count_html({ completed, late }) {
		const count = format_number(completed, null, 0);
		if (!late) return count;
		const text = __("{0} late", [format_number(late, null, 0)]);
		return `${count} <span class="text-ink-gray-4">·</span> <span class="text-ink-red-7">${text}</span>`;
	}

	// on time and late can't be told apart by a list filter, so both open the completed tasks
	open_outcome(outcome) {
		const project = this.overview.project;
		const filters = {
			"On Time": { project, status: "Completed" },
			Late: { project, status: "Completed" },
			"No Due Date": { project, status: "Completed", exp_end_date: ["is", "not set"] },
			Cancelled: { project, status: "Cancelled" },
		}[outcome];
		if (filters) this.overview.open_list("Task", filters);
		else this.overview.open_task_list();
	}

	outcome_colors() {
		return {
			"On Time": "var(--surface-green-7)",
			Late: "var(--surface-red-6)",
			"No Due Date": "var(--surface-gray-4)",
			"Still Open": "var(--surface-blue-7)",
			Cancelled: "var(--surface-gray-6)",
		};
	}

	open_assignee_tasks(user) {
		this.overview.open_task_list({ _assign: user ? ["like", `%${user}%`] : ["is", "not set"] });
	}

	// Overdue is worked out from the Expected End Date, as on the Overdue card
	open_status(status) {
		if (status === "Overdue") {
			this.overview.open_task_list({ exp_end_date: ["<", this.overview.data.as_of] });
		} else {
			this.overview.open_list("Task", { project: this.overview.project, status });
		}
	}

	status_colors() {
		return {
			Open: "var(--surface-blue-7)",
			Working: "var(--surface-blue-5)",
			"Pending Review": "var(--surface-violet-7)",
			Overdue: "var(--surface-red-6)",
			Completed: "var(--surface-green-7)",
			Cancelled: "var(--surface-gray-5)",
		};
	}

	error($panel) {
		$('<div class="po-empty po-error">').text(__("Could not load tasks")).appendTo($panel);
	}
};
