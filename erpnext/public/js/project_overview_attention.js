// The Overview tab's task list under the stat cards: Needs Attention while the project runs, ranked
// by the server with one reason each, and Loose Ends (tasks left open) once it is completed or cancelled
erpnext.ProjectOverviewAttention = class ProjectOverviewAttention {
	constructor(overview) {
		this.overview = overview;
	}

	render(data) {
		if (data.delivery) {
			this.render_list(data.loose_ends, {
				title: __("Loose Ends"),
				subtitle:
					data.delivery.status === "Cancelled"
						? __("Tasks still open on this cancelled project")
						: __("Tasks still open on this completed project"),
				badge_label: __("Status"),
				badges: this.status_badges(),
			});
		} else {
			const attention = data.needs_attention;
			this.render_list(attention, {
				title: __("Needs Attention"),
				subtitle:
					attention &&
					__("Overdue, blocked, unassigned, or due in the next {0} days", [
						attention.due_soon_days,
					]),
				badge_label: __("Reason"),
				badges: this.reasons(),
			});
		}
	}

	render_list(attention, { title, subtitle, badge_label, badges }) {
		// with nothing to chase the section is left out entirely; a failed load still says so
		if (attention?.total === 0) return;

		const $section = $('<section class="po-section">').appendTo(this.overview.$root);
		this.overview.section_head($section, {
			title,
			subtitle: attention ? subtitle : "",
			action: this.overview.report_link(__("Task List"), () => this.overview.open_task_list()),
		});

		if (!attention) {
			$('<div class="po-note po-error">').text(__("Could not load tasks")).appendTo($section);
			return;
		}
		this.make_list($("<div>").appendTo($section), attention.tasks, { badge_label, badges }).refresh();
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

	make_list($wrapper, tasks, { badge_label, badges }) {
		const rows = tasks.map((task) => ({ ...task, ...badges[task.reason] }));
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
					label: badge_label,
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
					width: "100px",
					render: (row) => this.due_html(row),
				},
				{
					label: __("Delayed By"),
					align: "right",
					width: "100px",
					render: (row) => this.delay_html(row),
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

	status_badges() {
		return {
			Open: { label: __("Open"), theme: "gray" },
			Working: { label: __("Working"), theme: "blue" },
			"Pending Review": { label: __("Pending Review"), theme: "violet" },
		};
	}

	// the same overlapping group the list view shows for Assigned To
	assignee_html(users) {
		if (!users.length) return "";
		const avatars = users.map((user) => {
			const { fullname, image } = frappe.user_info(user);
			return { label: fullname, image };
		});
		return frappe.ui.avatar_group.html({ avatars, max: 3, size: "sm" });
	}

	due_html({ due_date }) {
		if (!due_date) return "";
		const due = moment(due_date);
		return due.format(due.year() === moment().year() ? "D MMM" : "D MMM YYYY");
	}

	// plain text: the Overdue badge already marks the row, so the delay isn't coloured again
	delay_html({ days_late }) {
		if (!days_late) return "";
		return days_late === 1 ? __("1 day") : __("{0} days", [days_late]);
	}
};
