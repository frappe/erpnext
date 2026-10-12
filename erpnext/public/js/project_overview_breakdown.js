// The Overview tab's Tasks by Status donut and Open Tasks by Assignee list, side by side
erpnext.ProjectOverviewBreakdown = class ProjectOverviewBreakdown {
	constructor(overview) {
		this.overview = overview;
	}

	render(by_status, workload) {
		const $row = $('<div class="po-section po-two-col">').appendTo(this.overview.$root);
		this.render_status(this.overview.panel($row, __("Tasks by Status")), by_status);
		this.render_workload(this.overview.panel($row, __("Open Tasks by Assignee")), workload);
	}

	render_status($panel, by_status) {
		if (!by_status) return this.error($panel);

		const colors = this.status_colors();
		$panel.append(
			frappe.ui.donut({
				segments: by_status.statuses.map(({ status, count }) => ({
					status,
					label: __(status),
					value: count,
					color: colors[status],
				})),
				center: { value: String(by_status.total), label: __("tasks") },
				size: 196,
				onclick: (segment) => this.open_status(segment.status),
			})
		);
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
