const ASSIGNEE_AVATARS = 3;

// The Overview tab's Needs Attention list: open tasks ranked by the server, one reason each
erpnext.ProjectOverviewAttention = class ProjectOverviewAttention {
	constructor(overview) {
		this.overview = overview;
	}

	render(attention) {
		// with nothing to chase the section is left out entirely; a failed load still says so
		if (attention?.total === 0) return;

		const $section = $('<section class="po-section">').appendTo(this.overview.$root);
		this.overview.section_head($section, {
			title: __("Needs Attention"),
			subtitle: attention
				? __("Overdue, blocked, unassigned, or due in the next {0} days", [attention.due_soon_days])
				: "",
			action: this.overview.report_link(__("Task List"), () => this.overview.open_task_list()),
		});

		if (!attention) {
			$('<div class="po-note po-error">').text(__("Could not load tasks")).appendTo($section);
			return;
		}
		this.make_list($("<div>").appendTo($section), attention.tasks).refresh();
		// only the top rows are sent; the rest are left to the Task List linked above
		if (attention.total > attention.tasks.length) {
			$('<div class="po-note po-attention-more">')
				.text(
					__("Showing {0} of {1}. Open the Task List for the rest.", [
						attention.tasks.length,
						attention.total,
					])
				)
				.appendTo($section);
		}
	}

	make_list($wrapper, tasks) {
		const reasons = this.reasons();
		const rows = tasks.map((task) => ({ ...task, ...reasons[task.reason] }));
		return new frappe.ui.EmbeddedList({
			wrapper: $wrapper,
			// the rows are already ranked by the server and sent with the rest of the overview
			get_data: () => Promise.resolve(rows),
			// every row sent is shown, so the list has no Load More
			page_size: rows.length,
			show_search: false,
			on_row_click: (row) => frappe.set_route("Form", "Task", row.task),
			columns: [
				{
					label: __("Task"),
					fieldname: "subject",
					type: "link",
					url: (row) => frappe.utils.get_form_link("Task", row.task),
				},
				{
					label: __("Reason"),
					fieldname: "label",
					type: "badge",
					color: (row) => row.theme,
					width: "110px",
				},
				{
					label: __("Assigned To"),
					width: "160px",
					render: (row) => this.assignee_html(row.assigned_to),
				},
				{
					label: __("Due Date"),
					align: "right",
					width: "120px",
					render: (row) => this.due_html(row),
				},
			],
		});
	}

	reasons() {
		return {
			Overdue: { label: __("Overdue"), theme: "red" },
			Blocked: { label: __("Blocked"), theme: "orange" },
			Unassigned: { label: __("Unassigned"), theme: "gray" },
			"Due Soon": { label: __("Due Soon"), theme: "blue" },
		};
	}

	// one avatar per assignee, named in its tooltip; past three, the rest are counted
	assignee_html(users) {
		if (!users.length) return `<span class="text-ink-gray-5">${__("Unassigned")}</span>`;
		const avatars = users.slice(0, ASSIGNEE_AVATARS).map((user) => {
			const { fullname, image } = frappe.user_info(user);
			return frappe.ui.avatar.html({ label: fullname, image, size: "sm" });
		});
		const others = users.length - ASSIGNEE_AVATARS;
		const more = others > 0 ? `<span class="po-assignee-more">+${others}</span>` : "";
		return `<span class="po-assignees">${avatars.join("")}${more}</span>`;
	}

	due_html({ due_date, days_late }) {
		if (!due_date) return '<span class="text-ink-gray-4">—</span>';
		const due = moment(due_date);
		const text = due.format(due.year() === moment().year() ? "D MMM" : "D MMM YYYY");
		if (!days_late) return text;
		return `<span class="text-ink-red-7">${text} · ${__("{0}d late", [days_late])}</span>`;
	}
};
