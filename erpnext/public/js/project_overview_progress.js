// a gap wider than this many points behind plan reads as a warning
const BEHIND_PLAN_WARNING = 5;

// The Overview tab's Planned vs Completed chart: cumulative % complete over time, worked out by the server
erpnext.ProjectOverviewProgress = class ProjectOverviewProgress {
	constructor(overview) {
		this.overview = overview;
	}

	render(chart) {
		// nothing to plot (Manual % Complete, or only cancelled tasks), so the panel is left out
		if (chart && !chart.points.length) return;

		const $panel = $('<div class="po-panel bg-surface-base">').appendTo(
			$('<div class="po-section">').appendTo(this.overview.$root)
		);
		if (!chart) {
			this.overview.section_head($panel, { title: __("Planned vs Completed") });
			this.overview.error_text(__("Could not load tasks")).addClass("po-empty").appendTo($panel);
			return;
		}

		this.chart = chart;
		const { has_plan } = chart;
		const $head = this.overview.section_head($panel, {
			// without a plan only one line is drawn, so the title says just that
			title: has_plan ? __("Planned vs Completed") : __("Completed over Time"),
			// without a plan, a way to the tasks that need dates, like the tab's other links
			action: has_plan ? null : this.set_due_dates_link(),
		});
		$head.find(".po-title").append(this.about_icon());
		$('<div class="po-subtitle">').append(this.subtitle()).appendTo($head);

		this.render_chart($('<div class="po-chart">').appendTo($panel)[0]);
	}

	render_chart(wrapper) {
		const { points, has_plan, today_index } = this.chart;
		const labels = points.map((point) => this.date_text(point.date));
		const datasets = [
			{
				name: __("Completed"),
				values: points.map((point) => point.completed),
				lineOptions: { regionFill: 1, showGaps: 1 },
			},
		];
		const colors = [this.token_color("--surface-green-7")];
		if (has_plan) {
			datasets.unshift({
				name: __("Planned"),
				values: points.map((point) => point.planned),
				lineOptions: { dashed: 1 },
			});
			colors.unshift(this.token_color("--surface-gray-5"));
		}

		frappe.utils.make_chart(wrapper, {
			type: "line",
			height: 220,
			colors,
			data: {
				labels,
				datasets,
				xMarkers: today_index == null ? [] : [{ label: __("Today"), value: labels[today_index] }],
			},
			axisOptions: {
				yAxisRange: { min: 0, max: 100 },
				numberFormatter: (value) => this.percent_text(value),
			},
			tooltipOptions: {
				formatTooltipY: (value) => (value == null ? "" : this.percent_text(value)),
			},
		});
	}

	// frappe-charts blends colours from literal values, so a design token is read as the theme sets it
	token_color(token) {
		return getComputedStyle(document.documentElement).getPropertyValue(token).trim();
	}

	// where the project stands today, and the gap to plan or why there is no plan
	subtitle() {
		const { points, has_plan, today_index } = this.chart;
		const latest = Math.max(
			points.findLastIndex((point) => point.completed != null),
			0
		);
		const point = points[today_index ?? latest];
		const completed = this.percent_text(point.completed || 0);
		const prefix = today_index == null ? "" : __("Today") + ": ";

		const $subtitle = $("<span>");
		if (!has_plan) {
			const { undated, total } = this.chart;
			const note = __("No plan: {0} of {1} tasks have no Expected End Date", [undated, total]);
			return $subtitle.text(prefix + __("{0} completed", [completed]) + " · " + note);
		}
		const planned = this.percent_text(point.planned || 0);
		return $subtitle
			.text(prefix + __("{0} completed of {1} planned", [completed, planned]) + " · ")
			.append(this.gap_text(point));
	}

	gap_text({ planned, completed }) {
		const $gap = $('<span class="po-chart-gap">');
		const gap = Math.round((completed || 0) - (planned || 0));
		if (!gap) return $gap.text(__("On plan"));
		if (gap > 0) return $gap.addClass("text-ink-green-7").text(__("{0} pts ahead", [gap]));
		return $gap
			.addClass(-gap > BEHIND_PLAN_WARNING ? "text-ink-amber-7" : "text-ink-gray-7")
			.text(__("{0} pts behind", [-gap]));
	}

	set_due_dates_link() {
		return this.overview.report_link(__("Set Due Dates"), () =>
			this.overview.open_task_list({ exp_end_date: ["is", "not set"] })
		);
	}

	// what the lines measure and which dates they use, kept out of the way in a tooltip
	about_icon() {
		const $icon = $('<span class="po-title-info">').html(frappe.utils.icon("info", "sm"));
		frappe.ui.tooltip($icon, { text: this.about_text(), text_align: "start", delay: 100 });
		return $icon;
	}

	about_text() {
		const { method, points, has_plan, completed_without_date } = this.chart;
		const measure = {
			"Task Completion": __("Cumulative % of tasks closed"),
			"Task Progress": __("Cumulative % of task progress"),
			"Task Weight": __("Cumulative % of task weight"),
		}[method];
		const weeks = points.length > 1 ? moment(points[1].date).diff(points[0].date, "weeks") : 1;
		const lines = [measure + ", " + (weeks > 1 ? __("every {0} weeks", [weeks]) : __("by week"))];
		if (has_plan) lines.push(__("Planned by Expected End Date"));
		lines.push(__("Completed by Completed On"));
		if (completed_without_date) {
			lines.push(__("{0} without Completed On use their last change", [completed_without_date]));
		}
		return lines.join("\n");
	}

	date_text(date) {
		const { points } = this.chart;
		const spans_years = moment(points[0].date).year() !== moment(points.at(-1).date).year();
		return moment(date).format(spans_years ? "D MMM YY" : "D MMM");
	}

	percent_text(value) {
		return format_number(value, null, value % 1 ? 1 : 0) + "%";
	}
};
