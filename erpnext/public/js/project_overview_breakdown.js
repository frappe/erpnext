// The Overview tab's task donut and per-person list: open work while the project runs, and how it was
// delivered once it is completed or cancelled
erpnext.ProjectOverviewBreakdown = class ProjectOverviewBreakdown {
	constructor(overview) {
		this.overview = overview;
	}

	render_tasks($parent, data) {
		if (data.delivery) {
			this.render_delivery(
				this.overview.panel($parent, __("Tasks by Outcome")),
				data.tasks_by_delivery
			);
		} else {
			this.render_status(this.overview.panel($parent, __("Tasks by Status")), data.tasks_by_status);
		}
	}

	render_people($parent, data) {
		const $panel = $('<div class="po-panel bg-surface-base">').appendTo($parent);
		const title = data.delivery ? __("Completed by Assignee") : __("Open Tasks by Assignee");
		const $head = this.overview.section_head($panel, { title });
		$head.find(".po-title").append(this.overview.info_icon(this.people_note()));
		if (data.delivery) {
			this.render_completed($panel, data.completed_by_assignee);
		} else {
			this.render_workload($panel, data.workload);
		}
	}

	people_note() {
		return __(
			"A task shared by several people counts for each of them. Group tasks are left out, as their subtasks carry the work."
		);
	}

	// billed against cost as the Costing tab adds them up, with the gross margin in the middle
	render_profitability($parent, profitability) {
		const $panel = $('<div class="po-panel bg-surface-base">').appendTo($parent);
		const $head = this.overview.section_head($panel, {
			title: __("Profitability"),
			action: this.overview.report_link(__("Costing"), () => this.overview.open_tab("costing_tab")),
		});
		$head
			.find(".po-title")
			.append(
				this.overview.info_icon(
					__(
						"Billed is the amount on Sales Invoices for this project. Cost is the time logged at costing rates, plus purchases and consumed material. Gross margin is Billed less Cost."
					)
				)
			);
		if (!profitability) return this.error($panel);

		const { currency, billed, cost, margin, margin_percent } = profitability;
		if (!billed && !cost) {
			$panel.append(
				frappe.ui.empty_state({ icon: "wallet", title: __("Nothing billed or spent yet") })
			);
			return;
		}
		const money = (value) => format_currency(value, currency, 0);
		const $chart = $('<div class="po-donut po-profit-donut">').toggleClass(
			"po-margin-negative",
			margin < 0
		);
		frappe.utils.make_chart($chart.appendTo($panel)[0], {
			type: "donut",
			height: 280,
			colors: ["var(--surface-blue-7)", "var(--surface-blue-4)"],
			data: { labels: [__("Billed"), __("Cost")], datasets: [{ values: [billed, cost] }] },
			center: {
				value: money(margin),
				label:
					margin_percent == null
						? __("Gross Margin")
						: __("Gross Margin {0}%", [format_number(margin_percent, null, 1)]),
			},
			tooltipOptions: { formatTooltipY: money },
		});
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

		this.people_list($panel, completed.rows, {
			count: (row) => __("{0} completed", [row.completed]),
			note: (row) => (row.late ? __("{0} late", [row.late]) : ""),
			empty: __("No completed tasks"),
			onclick: (row) => this.overview.open_list("Task", { name: ["in", row.tasks] }),
		});
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

		this.people_list($panel, workload.rows, {
			count: (row) => __("{0} open", [row.open]),
			note: (row) => (row.overdue ? __("{0} overdue", [row.overdue]) : ""),
			empty: __("No open tasks"),
			onclick: (row) => this.open_assignee_tasks(row.user),
		});
	}

	// one row per person: avatar, name, and their count with the overdue (or late) part in red; the row
	// opens their tasks
	people_list($panel, rows, { count, note, empty, onclick }) {
		if (!rows.length) {
			$panel.append(frappe.ui.empty_state({ icon: "users", title: empty }));
			return;
		}
		const $list = $('<div class="po-people">').appendTo($panel);
		rows.forEach((row) => {
			const { fullname, image } = row.user ? frappe.user_info(row.user) : {};
			const avatar = row.user
				? frappe.ui.avatar.html({ label: fullname, image, size: "lg", theme: "auto" })
				: frappe.ui.avatar.html({
						label: "?",
						title: __("Unassigned"),
						size: "lg",
						css_class: "po-avatar-unassigned",
				  });
			const $meta = $('<div class="po-person-meta">').text(count(row));
			if (note(row)) {
				$meta.append(" · ", $('<span class="text-ink-red-7">').text(note(row)));
			}
			$('<div class="po-person" role="button" tabindex="0">')
				.append(avatar)
				.append(
					$('<div class="po-person-text">')
						.append(
							$('<div class="po-person-name">')
								.toggleClass("is-unassigned", !row.user)
								.text(row.user ? fullname : __("Unassigned"))
						)
						.append($meta)
				)
				.on("click", () => onclick(row))
				.on("keydown", (e) => {
					if (e.key !== "Enter" && e.key !== " ") return;
					e.preventDefault();
					onclick(row);
				})
				.appendTo($list);
		});
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
