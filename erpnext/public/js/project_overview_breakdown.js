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
			this.render_workload($panel, $head, data.workload);
		}
	}

	people_note() {
		return __(
			"A task shared by several people counts for each of them. Group tasks are left out, as their subtasks carry the work."
		);
	}

	render_profitability($parent, profitability) {
		const $panel = $('<div class="po-panel bg-surface-base">').appendTo($parent);
		const $head = this.overview.section_head($panel, {
			title: __("Profitability"),
			action: this.overview.icon_link(__("Open Costing"), () => this.overview.open_tab("costing_tab")),
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
		this.overview.add_chart(
			frappe.utils.make_chart($chart.appendTo($panel)[0], {
				type: "donut",
				height: 280,
				colors: ["var(--surface-green-7)", "var(--surface-red-6)"],
				data: { labels: [__("Billed"), __("Cost")], datasets: [{ values: [billed, cost] }] },
				center: {
					value: money(margin),
					label:
						margin_percent == null
							? __("Gross Margin")
							: __("Gross Margin {0}%", [format_number(margin_percent, null, 1)]),
				},
				tooltipOptions: { formatTooltipY: money },
			})
		);
	}

	render_delivery($panel, by_delivery) {
		if (!by_delivery) return this.error($panel);

		const outcomes = this.outcomes();
		this.donut($panel, {
			slices: by_delivery.outcomes.map(({ outcome, count, tasks }) => ({
				label: outcomes[outcome].label,
				value: count,
				color: outcomes[outcome].color,
				onclick: () => this.overview.open_list("Task", { name: ["in", tasks] }),
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
			slices: by_status.statuses.map(({ status, count, tasks }) => ({
				label: __(status),
				value: count,
				color: colors[status] || "var(--surface-gray-4)",
				onclick: () => this.overview.open_list("Task", { name: ["in", tasks] }),
			})),
			total: by_status.total,
		});
	}

	// past maxSlices frappe-charts folds slices into 'Rest' and reorders them, breaking the index lookup
	donut($panel, { slices, total }) {
		this.overview.add_chart(
			frappe.utils.make_chart($('<div class="po-donut">').appendTo($panel)[0], {
				type: "donut",
				height: 280,
				colors: slices.map((slice) => slice.color),
				data: {
					labels: slices.map((slice) => slice.label),
					datasets: [{ values: slices.map((slice) => slice.value) }],
				},
				center: { value: format_number(total, null, 0), label: __("tasks") },
				maxSlices: slices.length,
				maxLegendPoints: slices.length,
				onClick: ({ index }) => slices[index].onclick(),
			})
		);
	}

	render_workload($panel, $head, workload) {
		if (!workload) return this.error($panel);

		let rows = workload.rows;
		if (rows.length > 5) {
			const unassigned = rows.find((row) => !row.user);
			rows = unassigned ? [...rows.slice(0, 4), unassigned] : rows.slice(0, 5);
			$head.append(
				this.overview.icon_link(__("Open Task List"), () =>
					this.overview.open_task_list({ is_group: 0 })
				)
			);
		}
		this.people_list($panel, rows, {
			count: (row) => __("{0} open", [row.open]),
			note: (row) => (row.overdue ? __("{0} overdue", [row.overdue]) : ""),
			empty: __("No open tasks"),
			onclick: (row) => this.overview.open_task_list({ name: ["in", row.tasks] }),
		});
	}

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

	// written out so the server's outcome labels are picked up for translation
	outcomes() {
		return {
			"On Time": { label: __("On Time"), color: "var(--surface-green-7)" },
			Late: { label: __("Late"), color: "var(--surface-red-6)" },
			"No Due Date": { label: __("No Due Date"), color: "var(--surface-gray-4)" },
			"Still Open": { label: __("Still Open"), color: "var(--surface-blue-7)" },
			Cancelled: { label: __("Cancelled"), color: "var(--surface-gray-6)" },
		};
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
