frappe.provide("erpnext");

const PROJECT_OVERVIEW_METHOD = "erpnext.projects.doctype.project.project_overview.get_project_overview";
const OPEN_TASK_STATUS = ["not in", ["Completed", "Cancelled", "Template"]];

frappe.ui.form.on("Project", {
	refresh(frm) {
		if (frm.is_new() || !frm.get_field("overview_html")) return;
		const can_read_tasks = frappe.model.can_read("Task");
		frm.toggle_display("overview_html", can_read_tasks);
		if (!can_read_tasks) return;

		if (!frm.project_overview) frm.project_overview = new erpnext.ProjectOverview(frm);
		frm.project_overview.refresh();
	},
	on_tab_change(frm) {
		frm.project_overview?.show();
	},
});

erpnext.ProjectOverview = class ProjectOverview {
	constructor(frm) {
		this.frm = frm;
		this.seq = 0;
		this.charts = [];
		this.progress = new erpnext.ProjectOverviewProgress(this);
		this.attention = new erpnext.ProjectOverviewAttention(this);
		this.breakdown = new erpnext.ProjectOverviewBreakdown(this);
	}

	refresh() {
		this.needs_refresh = true;
		this.show();
	}

	async show() {
		if (!this.is_active() || !this.needs_refresh) return;
		await frappe.require(["desk_charts.bundle.js", "desk_charts.bundle.css", "embedded_list.bundle.js"]);
		if (!this.is_active() || !this.needs_refresh) return;
		this.needs_refresh = false;
		if (this.project !== this.frm.doc.name) this.build();
		this.load();
	}

	is_active() {
		return this.frm.get_active_tab()?.df.fieldname === "overview_tab";
	}

	build() {
		this.destroy_charts();
		this.project = this.frm.doc.name;
		const $wrapper = this.frm.get_field("overview_html").$wrapper.empty();
		this.$root = $('<div class="project-overview">').appendTo($wrapper);
	}

	load() {
		const token = ++this.seq;
		this.render({ loading: true });
		frappe
			.xcall(PROJECT_OVERVIEW_METHOD, { project: this.project })
			.then((data) => ({ data }))
			.catch(() => ({ error: true }))
			.then((result) => {
				if (token === this.seq) this.render(result);
			});
	}

	render({ loading, error, data }) {
		this.destroy_charts();
		this.$root.empty().attr("aria-busy", loading ? "true" : "false");
		this.render_header(data);
		if (loading || error || data.errors.summary) {
			this.render_placeholders(loading);
		} else if (!data.summary.has_tasks) {
			this.render_no_tasks();
		} else if (data.summary.all_cancelled) {
			this.render_all_cancelled(data.summary.task_count);
		} else {
			this.data = data;
			this.render_stats(data.stats);
			this.render_sections(data);
		}
	}

	render_sections(data) {
		const chart = data.planned_vs_completed;
		const row = (css_class) => $(`<div class="po-section ${css_class}">`).appendTo(this.$root);
		if (this.progress.has_chart(chart)) {
			const $top = row("po-chart-row");
			this.progress.render($top, chart);
			this.breakdown.render_tasks($top, data);
			this.attention.render(data);
			const $bottom = row("po-two-col");
			this.breakdown.render_people($bottom, data);
			this.render_profitability($bottom, data);
		} else {
			this.attention.render(data);
			const $top = row("po-two-col");
			this.breakdown.render_tasks($top, data);
			this.render_profitability($top, data);
			this.breakdown.render_people(row(""), data);
		}
	}

	render_profitability($parent, data) {
		if (data.profitability || data.errors.profitability) {
			this.breakdown.render_profitability($parent, data.profitability);
		}
	}

	open_tab(fieldname) {
		this.frm.layout.tabs.find((tab) => tab.df.fieldname === fieldname)?.set_active();
	}

	render_header(data) {
		if (data?.summary?.all_cancelled) return;
		const items = [];
		if (data?.delivery) {
			items.push(
				data.delivery.status === "Cancelled"
					? this.cancelled_item(data.delivery)
					: this.delivery_item(data.delivery)
			);
		} else {
			const milestone = data?.summary?.has_tasks && data.milestone;
			if (milestone && (milestone.next || milestone.all_met))
				items.push(this.milestone_item(milestone));
			const range = this.date_range_text();
			if (range) items.push($("<span>").text(range));
		}
		if (!items.length) return;

		const $header = $('<div class="po-header">').appendTo(this.$root);
		items.forEach((item, i) => $header.append(i ? '<span class="po-header-divider"></span>' : "", item));
	}

	delivery_item({ finished_on, planned_end, days_late }) {
		const full = (date) => moment(date).format("D MMM YYYY");
		const $item = $('<span class="po-milestone">').append(frappe.utils.icon("circle-check", "sm"));
		$('<span class="po-milestone-link">')
			.text(finished_on ? __("Completed {0}", [full(finished_on)]) : __("Completed"))
			.appendTo($item);
		if (days_late != null) {
			let schedule = __("On time");
			if (days_late > 0) schedule = this.days_late_text(days_late);
			else if (days_late < 0) schedule = this.days_early_text(-days_late);
			$('<span class="po-milestone-due">')
				.toggleClass("po-error", days_late > 0)
				.text(schedule + " · " + __("planned {0}", [full(planned_end)]))
				.appendTo($item);
		}
		return $item;
	}

	cancelled_item({ percent_complete }) {
		const $item = $('<span class="po-milestone">').append(frappe.utils.icon("circle-x", "sm"));
		$('<span class="po-milestone-link">').text(__("Cancelled")).appendTo($item);
		const notes = [
			__("{0}% complete", [format_number(percent_complete, null, percent_complete % 1 ? 1 : 0)]),
		];
		const range = this.date_range_text();
		if (range) notes.push(__("planned {0}", [range]));
		$('<span class="po-milestone-due">').text(notes.join(" · ")).appendTo($item);
		return $item;
	}

	milestone_item({ next, all_met }) {
		const $item = $('<span class="po-milestone">').append(frappe.utils.icon("flag", "sm"));
		$("<span>").text(__("Next Milestone")).appendTo($item);
		$('<a class="po-milestone-link">')
			.text(next ? next.subject : __("All milestones met"))
			.on("click", () =>
				next
					? frappe.set_route("Form", "Task", next.task)
					: this.open_list("Task", { project: this.project, is_milestone: 1 })
			)
			.appendTo($item);
		if (next?.due_date) {
			$('<span class="po-milestone-due">')
				.toggleClass("po-error", next.days_left < 0)
				.text(this.milestone_due_text(next))
				.appendTo($item);
		}
		return $item;
	}

	milestone_due_text({ due_date, days_left }) {
		let relative = __("in {0} days", [days_left]);
		if (days_left < 0) relative = this.days_late_text(-days_left);
		else if (days_left === 0) relative = __("today");
		else if (days_left === 1) relative = __("tomorrow");
		return moment(due_date).format("D MMM") + " · " + relative;
	}

	date_range_text() {
		const { expected_start_date: start, expected_end_date: end } = this.frm.doc;
		const full = (date) => moment(date).format("D MMM YYYY");
		if (!start && !end) return "";
		if (!end) return __("From {0}", [full(start)]);
		if (!start) return __("Until {0}", [full(end)]);
		const same_year = moment(start).year() === moment(end).year();
		return moment(start).format(same_year ? "D MMM" : "D MMM YYYY") + " – " + full(end);
	}

	render_stats(stats, loading) {
		const delivery = stats && this.data.delivery;
		const cancelled = delivery?.status === "Cancelled";
		let labels = [__("Open Tasks"), __("Overdue"), __("Hours Logged")];
		if (cancelled) labels = [__("Tasks Delivered"), __("Hours Logged")];
		else if (delivery) labels = [__("Tasks Delivered"), __("On Time"), __("Hours Logged")];
		const failed = () => ({ value: "—", caption: this.error_text(__("Could not load tasks")) });
		let cards = labels.map((label) => (loading ? { loading } : failed()));
		const hours = stats?.hours && this.hours_card(stats);
		if (cancelled) {
			cards = [this.delivered_card(delivery), hours];
		} else if (delivery) {
			cards = [this.delivered_card(delivery), this.on_time_card(delivery), hours];
		} else if (stats) {
			cards = [this.open_tasks_card(stats), this.overdue_card(stats), hours];
		}
		cards.forEach((card, i) => card && (card.label = labels[i]));
		cards = cards.filter(Boolean);
		if (stats && this.data.unbilled) cards.push(this.unbilled_card(this.data.unbilled));
		this.$root.append(frappe.ui.stat_cards({ items: cards }));
	}

	open_tasks_card({ open_tasks: { count, due_soon, due_soon_days } }) {
		let caption = __("None open");
		if (count) {
			caption = due_soon
				? __("{0} due in the next {1} days", [due_soon, due_soon_days])
				: __("None due in the next {0} days", [due_soon_days]);
		}
		return {
			value: format_number(count, null, 0),
			caption,
			onclick: () => this.open_task_list(),
		};
	}

	overdue_card({ overdue: { count, oldest_days_late, tasks } }) {
		const caption = count
			? __("Oldest {0}", [this.days_late_text(oldest_days_late)])
			: __("Nothing overdue");
		return {
			value: count ? $('<span class="po-error">').text(format_number(count, null, 0)) : "0",
			caption,
			// by name, as a due-date filter can't leave out tasks still awaiting review
			onclick: count ? () => this.open_list("Task", { name: ["in", tasks] }) : null,
		};
	}

	delivered_card({ total, completed, cancelled, open }) {
		const notes = [];
		if (cancelled) notes.push(__("{0} cancelled", [cancelled]));
		if (open) notes.push(__("{0} still open", [open]));
		return {
			value: __("{0} of {1}", [format_number(completed, null, 0), format_number(total, null, 0)]),
			caption: notes.length ? notes.join(" · ") : __("All tasks completed"),
			onclick: () => this.open_list("Task", { project: this.project, status: "Completed" }),
		};
	}

	on_time_card({ rated, late }) {
		if (!rated) return { value: "—", caption: __("No Expected End Dates to compare") };
		let caption = __("Every task finished on time");
		if (late) caption = late === 1 ? __("1 task finished late") : __("{0} tasks finished late", [late]);
		return {
			value: Math.round(((rated - late) / rated) * 100) + "%",
			caption,
			onclick: () => this.open_list("Task", { project: this.project, status: "Completed" }),
		};
	}

	hours_card({ hours: { logged, expected } }) {
		let caption = __("No Expected Time to compare");
		if (expected && logged > expected) {
			caption = __("{0} over {1} expected", [
				this.hours_text(logged - expected),
				this.hours_text(expected),
			]);
		} else if (expected) {
			caption = __("{0}% of {1} expected", [
				Math.round((logged / expected) * 100),
				this.hours_text(expected),
			]);
		}
		return {
			value: this.hours_text(logged),
			caption,
			onclick: () => this.open_list("Timesheet", { project: this.project, docstatus: 1 }),
		};
	}

	unbilled_card({ amount, hours, currency }) {
		return {
			label: __("Unbilled"),
			value: format_currency(amount, currency, 0),
			caption: !amount
				? __("All billable time invoiced")
				: hours == null
				? __("Billable time not invoiced")
				: __("{0} of billable time not invoiced", [this.hours_text(hours)]),
			onclick: () =>
				this.open_list("Timesheet", {
					"Timesheet Detail.project": this.project,
					"Timesheet Detail.is_billable": 1,
					"Timesheet Detail.sales_invoice": ["is", "not set"],
					docstatus: 1,
				}),
		};
	}

	render_placeholders(loading) {
		this.render_stats(null, loading);
		const $panels = $('<div class="po-section po-two-col">').appendTo(this.$root);
		const titles = [
			__("Planned vs Completed"),
			__("Needs Attention"),
			__("Tasks by Status"),
			__("Open Tasks by Assignee"),
		];
		titles.forEach((title) => {
			const $panel = this.panel($panels, title);
			if (loading) $panel.append(frappe.ui.skeleton({ width: "100%", height: "150px" }));
			else this.error_text(__("Could not load tasks")).addClass("po-empty").appendTo($panel);
		});

		if (!loading) this.render_retry();
	}

	render_retry() {
		$('<div class="po-section po-retry">')
			.append(
				$("<span>").text(
					__("Could not load the overview. Project details are still on the other tabs.")
				)
			)
			.append(frappe.ui.button({ label: __("Retry"), size: "sm", onclick: () => this.load() }))
			.appendTo(this.$root);
	}

	render_no_tasks() {
		const actions = frappe.model.can_create("Task")
			? [{ label: __("New Task"), icon: "plus", onclick: () => this.frm.events.create_task(this.frm) }]
			: [];
		this.$root.append(
			frappe.ui.empty_state({
				icon: "square-check",
				title: __("No tasks yet"),
				description: __(
					"Progress, deadlines, workload and costs for this project will show up here once tasks are added."
				),
				actions,
			})
		);
	}

	render_all_cancelled(count) {
		this.$root.append(
			frappe.ui.empty_state({
				icon: "circle-x",
				title: __("All tasks were cancelled"),
				description: __(
					"None of this project's {0} tasks went ahead, so there is no progress or workload to show.",
					[count]
				),
				actions: [
					{
						label: __("View Tasks"),
						onclick: () => this.open_list("Task", { project: this.project }),
					},
				],
			})
		);
	}

	section_head($parent, { title, subtitle, action }) {
		const $head = $('<div class="po-head">').appendTo($parent);
		const $text = $('<div class="po-head-text">').appendTo($head);
		$('<div class="po-title">').text(title).appendTo($text);
		if (subtitle) $('<div class="po-subtitle">').text(subtitle).appendTo($text);
		if (action) $head.append(action);
		return $head;
	}

	add_chart(chart) {
		this.charts.push(chart);
		return chart;
	}

	destroy_charts() {
		this.charts.forEach((chart) => chart.destroy());
		this.charts = [];
	}

	info_icon(text) {
		const $icon = $('<span class="po-title-info">').html(frappe.utils.icon("info", "sm"));
		frappe.ui.tooltip($icon, { text, text_align: "start", delay: 100 });
		return $icon;
	}

	report_link(label, onclick) {
		return frappe.ui.button({
			label,
			variant: "ghost",
			size: "sm",
			icon_right: "arrow-up-right",
			onclick,
		});
	}

	icon_link(tooltip, onclick) {
		return frappe.ui.button({
			icon: "arrow-up-right",
			variant: "ghost",
			size: "sm",
			tooltip,
			onclick,
		});
	}

	panel($parent, title) {
		const $panel = $('<div class="po-panel bg-surface-base">').appendTo($parent);
		$('<div class="po-title">').text(title).appendTo($panel);
		return $panel;
	}

	error_text(text) {
		return $('<span class="po-error">').text(text);
	}

	days_late_text(days) {
		return days === 1 ? __("1 day late") : __("{0} days late", [days]);
	}

	days_early_text(days) {
		return days === 1 ? __("1 day early") : __("{0} days early", [days]);
	}

	hours_text(hours) {
		return __("{0} h", [format_number(hours, null, hours % 1 ? 1 : 0)]);
	}

	open_task_list(filters = {}) {
		this.open_list("Task", { project: this.project, status: OPEN_TASK_STATUS, ...filters });
	}

	open_list(doctype, filters) {
		frappe.route_options = filters;
		frappe.set_route("List", doctype);
	}
};
