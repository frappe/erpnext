const BEHIND_PLAN_WARNING = 5;

erpnext.ProjectOverviewProgress = class ProjectOverviewProgress {
	constructor(overview) {
		this.overview = overview;
	}

	has_chart(chart) {
		return !chart || chart.points.length > 0;
	}

	render($parent, chart) {
		const $panel = $('<div class="po-panel bg-surface-base">').appendTo($parent);
		if (!chart) {
			this.overview.section_head($panel, { title: __("Planned vs Completed") });
			this.overview.error_text(__("Could not load tasks")).addClass("po-empty").appendTo($panel);
			return;
		}

		this.chart = chart;
		const { has_plan } = chart;
		const $head = this.overview.section_head($panel, {
			title: has_plan ? __("Planned vs Completed") : __("Completed over Time"),
		});
		$head.find(".po-title").append(this.overview.info_icon(this.about_text()));
		$('<div class="po-subtitle">').append(this.subtitle()).appendTo($head.find(".po-head-text"));

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
		const colors = ["var(--surface-green-7)"];
		if (has_plan) {
			datasets.unshift({
				name: __("Planned"),
				values: points.map((point) => point.planned),
				lineOptions: { dashed: 1 },
			});
			colors.unshift("var(--surface-gray-5)");
		}

		this.overview.add_chart(
			frappe.utils.make_chart(wrapper, {
				type: "line",
				height: 270,
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
			})
		);
	}

	subtitle() {
		const delivery = this.overview.data.delivery;
		if (delivery) return this.delivery_subtitle(delivery);

		const { points, has_plan, today_index } = this.chart;
		const latest = Math.max(
			points.findLastIndex((point) => point.completed != null),
			0
		);
		const point = points[today_index ?? latest];
		const completed = this.percent_text(point.completed || 0);

		const $subtitle = $("<span>");
		if (!has_plan) {
			const { undated, total } = this.chart;
			return $subtitle.text(__("{0} done", [completed]) + " · ").append(
				$('<a class="po-subtitle-link">')
					.text(__("{0} of {1} tasks need a due date", [undated, total]))
					.on("click", () => this.overview.open_task_list({ exp_end_date: ["is", "not set"] }))
			);
		}
		const planned = this.percent_text(point.planned || 0);
		return $subtitle
			.text(__("{0} done of {1} planned", [completed, planned]) + " · ")
			.append(this.gap_text(point));
	}

	delivery_subtitle({ days_late, finished_on }) {
		const parts = [];
		if (days_late > 0) {
			parts.push(
				days_late === 1
					? __("Finished 1 day after plan")
					: __("Finished {0} days after plan", [days_late])
			);
		} else if (days_late < 0) {
			parts.push(
				days_late === -1
					? __("Finished 1 day ahead of plan")
					: __("Finished {0} days ahead of plan", [-days_late])
			);
		} else if (days_late === 0) {
			parts.push(__("Finished on plan"));
		} else if (finished_on) {
			parts.push(__("Finished {0}", [moment(finished_on).format("D MMM YYYY")]));
		}

		const { has_plan, undated, total } = this.chart;
		if (!has_plan) {
			parts.push(__("No plan: {0} of {1} tasks have no Expected End Date", [undated, total]));
			return $("<span>").text(parts.join(" · "));
		}

		const { worst_gap } = this.chart;
		if (!worst_gap) return $("<span>").text(parts.join(" · "));
		const $subtitle = $("<span>").text(parts.length ? parts.join(" · ") + " · " : "");
		const gap = Math.round(worst_gap.points);
		if (gap <= 0) {
			return $subtitle.append(
				$('<span class="po-chart-gap text-ink-green-7">').text(__("Never behind plan"))
			);
		}
		return $subtitle.append(
			$('<span class="po-chart-gap">')
				.addClass(gap > BEHIND_PLAN_WARNING ? "text-ink-amber-7" : "text-ink-gray-7")
				.text(__("At most {0} pts behind, on {1}", [gap, moment(worst_gap.date).format("D MMM")]))
		);
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
