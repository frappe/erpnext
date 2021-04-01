frappe.pages['patient-progress'].on_page_load = function(wrapper) {

	frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Patient Progress')
	});

	let patient_progress = new PatientProgress(wrapper);
	$(wrapper).bind('show', ()=> {
		patient_progress.show();
	});
};

class PatientProgress {

	constructor(wrapper) {
		this.wrapper = $(wrapper);
		this.page = wrapper.page;
		this.sidebar = this.wrapper.find('.layout-side-section');
		this.main_section = this.wrapper.find('.layout-main-section');
	}

	show() {
		frappe.breadcrumbs.add('Healthcare');
		this.sidebar.empty();

		let me = this;
		let patient = frappe.ui.form.make_control({
			parent: me.sidebar,
			df: {
				fieldtype: 'Link',
				options: 'Patient',
				fieldname: 'patient',
				placeholder: __('Select Patient'),
				only_select: true,
				change: () => {
					me.patient_id = '';
					if (me.patient_id != patient.get_value() && patient.get_value()) {
						me.start = 0;
						me.patient_id = patient.get_value();
						me.make_patient_profile();
					}
				}
			}
		});
		patient.refresh();

		if (frappe.route_options && !this.patient) {
			patient.set_value(frappe.route_options.patient);
			this.patient_id = frappe.route_options.patient;
		}

		this.sidebar.find('[data-fieldname="patient"]').append('<div class="patient-info"></div>');
	}

	make_patient_profile() {
		this.page.set_title(__('Patient Progress'));
		this.main_section.empty().append(frappe.render_template('patient_progress'));
		this.render_patient_details();
		this.render_heatmap();
		this.render_percentage_chart('therapy_type', 'Therapy Type Distribution');
		this.create_percentage_chart_filters();
		this.show_therapy_progress();
		this.show_assessment_results();
		this.show_therapy_assessment_correlation();
		this.show_assessment_parameter_progress();
	}

	get_patient_info() {
		return frappe.xcall('frappe.client.get', {
			doctype: 'Patient',
			name: this.patient_id
		}).then((patient) => {
			if (patient) {
				this.patient = patient;
			}
		});
	}

	get_therapy_sessions_count() {
		return frappe.xcall(
			'erpnext.healthcare.page.patient_progress.patient_progress.get_therapy_sessions_count', {
				patient: this.patient_id,
			}
		).then(data => {
			if (data) {
				this.total_therapy_sessions = data.total_therapy_sessions;
				this.therapy_sessions_this_month = data.therapy_sessions_this_month;
			}
		});
	}

	render_patient_details() {
		this.get_patient_info().then(() => {
			this.get_therapy_sessions_count().then(() => {
				$('.patient-info').empty().append(frappe.render_template('patient_progress_sidebar', {
					patient_image: this.patient.image,
					patient_name: this.patient.patient_name,
					patient_gender: this.patient.sex,
					patient_mobile: this.patient.mobile,
					total_therapy_sessions: this.total_therapy_sessions,
					therapy_sessions_this_month: this.therapy_sessions_this_month
				}));

				this.setup_patient_profile_links();
			});
		});
	}

	setup_patient_profile_links() {
		this.wrapper.find('.patient-profile-link').on('click', () => {
			frappe.set_route('Form', 'Patient', this.patient_id);
		});

		this.wrapper.find('.therapy-plan-link').on('click', () => {
			frappe.route_options = {
				'patient': this.patient_id,
				'docstatus': 1
			};
			frappe.set_route('List', 'Therapy Plan');
		});

		this.wrapper.find('.patient-history').on('click', () => {
			frappe.route_options = {
				'patient': this.patient_id
			};
			frappe.set_route('patient_history');
		});
	}

	render_heatmap() {
		this.heatmap = new frappe.Chart('.patient-heatmap', {
			type: 'heatmap',
			countLabel: 'Interactions',
			data: {},
			discreteDomains: 0
		});
		this.update_heatmap_data();
		this.create_heatmap_chart_filters();
	}

	update_heatmap_data(date_from) {
		frappe.xcall('erpnext.healthcare.page.patient_progress.patient_progress.get_patient_heatmap_data', {
			patient: this.patient_id,
			date: date_from || frappe.datetime.year_start(),
		}).then((data) => {
			this.heatmap.update( {dataPoints: data} );
		});
	}

	create_heatmap_chart_filters() {
		this.get_patient_info().then(() => {
			let filters = [
				{
					label: frappe.dashboard_utils.get_year(frappe.datetime.now_date()),
					options: frappe.dashboard_utils.get_years_since_creation(this.patient.creation),
					action: (selected_item) => {
						this.update_heatmap_data(frappe.datetime.obj_to_str(selected_item));
					}
				},
			];
			frappe.dashboard_utils.render_chart_filters(filters, 'chart-filter', '.heatmap-container');
		});
	}

	render_percentage_chart(field, title) {
		frappe.xcall(
			'erpnext.healthcare.page.patient_progress.patient_progress.get_therapy_sessions_distribution_data', {
				patient: this.patient_id,
				field: field
			}
		).then(chart => {
			if (chart.labels.length) {
				this.percentage_chart = new frappe.Chart('.therapy-session-percentage-chart', {
					title: title,
					type: 'percentage',
					data: {
						labels: chart.labels,
						datasets: chart.datasets
					},
					truncateLegends: 1,
					barOptions: {
						height: 11,
						depth: 1
					},
					height: 160,
					maxSlices: 8,
					colors: ['#5e64ff', '#743ee2', '#ff5858', '#ffa00a', '#feef72', '#28a745', '#98d85b', '#a9a7ac'],
				});
			} else {
				this.wrapper.find('.percentage-chart-container').hide();
			}
		});
	}

	create_percentage_chart_filters() {
		let filters = [
			{
				label: 'Therapy Type',
				options: ['Therapy Type', 'Exercise Type'],
				fieldnames: ['therapy_type', 'exercise_type'],
				action: (selected_item, fieldname) => {
					let title = selected_item + ' Distribution';
					this.render_percentage_chart(fieldname, title);
				}
			},
		];
		frappe.dashboard_utils.render_chart_filters(filters, 'chart-filter', '.percentage-chart-container');
	}

	create_time_span_filters(action_method, parent) {
		let chart_control = $(parent).find('.chart-control');
		let filters = [
			{
				label: 'Last Month',
				options: ['Select Date Range', 'Last Week', 'Last Month', 'Last Quarter', 'Last Year'],
				action: (selected_item) => {
					if (selected_item === 'Select Date Range') {
						this.render_date_range_fields(action_method, chart_control);
					} else {
						// hide date range field if visible
						let date_field = $(parent).find('.date-field');
						if (date_field.is(':visible')) {
							date_field.hide();
						}
						this[action_method](selected_item);
					}
				}
			}
		];
		frappe.dashboard_utils.render_chart_filters(filters, 'chart-filter', chart_control, 1);
	}

	render_date_range_fields(action_method, parent) {
		let date_field = $(parent).find('.date-field');

		if (!date_field.length) {
			let date_field_wrapper = $(
				`<div class="date-field pull-right"></div>`
			).appendTo(parent);

			let date_range_field = frappe.ui.form.make_control({
				df: {
					fieldtype: 'DateRange',
					fieldname: 'from_date',
					placeholder: 'Date Range',
					input_class: 'input-xs',
					reqd: 1,
					change: () => {
						let selected_date_range = date_range_field.get_value();
						if (selected_date_range && selected_date_range.length === 2) {
							this[action_method](selected_date_range);
						}
					}
				},
				parent: date_field_wrapper,
				render_input: 1
			});
		} else if (!date_field.is(':visible')) {
			date_field.show();
		}
	}

	show_therapy_progress() {
		let me = this;
		let therapy_type = frappe.ui.form.make_control({
			parent: $('.therapy-type-search'),
			df: {
				fieldtype: 'Link',
				options: 'Therapy Type',
				fieldname: 'therapy_type',
				placeholder: __('Select Therapy Type'),
				only_select: true,
				change: () => {
					if (me.therapy_type != therapy_type.get_value() && therapy_type.get_value()) {
						me.therapy_type = therapy_type.get_value();
						me.render_therapy_progress_chart();
					}
				}
			}
		});
		therapy_type.refresh();
		this.create_time_span_filters('render_therapy_progress_chart', '.therapy-progress');
	}

	render_therapy_progress_chart(time_span='Last Month') {
		if (!this.therapy_type) return;

		frappe.xcall(
			'erpnext.healthcare.page.patient_progress.patient_progress.get_therapy_progress_data', {
				patient: this.patient_id,
				therapy_type: this.therapy_type,
				time_span: time_span
			}
		).then(chart => {
			let data = {
				labels: chart.labels,
				datasets: chart.datasets
			}
			let parent = '.therapy-progress-line-chart';
			if (!chart.labels.length) {
				this.show_null_state(parent);
			} else {
				if (!this.therapy_line_chart) {
					this.therapy_line_chart = new frappe.Chart(parent, {
						type: 'axis-mixed',
						height: 250,
						data: data,
						lineOptions: {
							regionFill: 1
						},
						axisOptions: {
							xIsSeries: 1
						},
					});
				} else {
					$(parent).find('.chart-container').show();
					$(parent).find('.chart-empty-state').hide();
					this.therapy_line_chart.update(data);
				}
			}
		});
	}

	show_assessment_results() {
		let me = this;
		let assessment_template = frappe.ui.form.make_control({
			parent: $('.assessment-template-search'),
			df: {
				fieldtype: 'Link',
				options: 'Patient Assessment Template',
				fieldname: 'assessment_template',
				placeholder: __('Select Assessment Template'),
				only_select: true,
				change: () => {
					if (me.assessment_template != assessment_template.get_value() && assessment_template.get_value()) {
						me.assessment_template = assessment_template.get_value();
						me.render_assessment_result_chart();
					}
				}
			}
		});
		assessment_template.refresh();
		this.create_time_span_filters('render_assessment_result_chart', '.assessment-results');
	}

	render_assessment_result_chart(time_span='Last Month') {
		if (!this.assessment_template) return;

		frappe.xcall(
			'erpnext.healthcare.page.patient_progress.patient_progress.get_patient_assessment_data', {
				patient: this.patient_id,
				assessment_template: this.assessment_template,
				time_span: time_span
			}
		).then(chart => {
			let data = {
				labels: chart.labels,
				datasets: chart.datasets,
				yMarkers: [
					{ label: 'Max Score', value: chart.max_score }
				],
			}
			let parent = '.assessment-results-line-chart';
			if (!chart.labels.length) {
				this.show_null_state(parent);
			} else {
				if (!this.assessment_line_chart) {
					this.assessment_line_chart = new frappe.Chart(parent, {
						type: 'axis-mixed',
						height: 250,
						data: data,
						lineOptions: {
							regionFill: 1
						},
						axisOptions: {
							xIsSeries: 1
						},
						tooltipOptions: {
							formatTooltipY: d => d + __(' out of ') + chart.max_score
						}
					});
				} else {
					$(parent).find('.chart-container').show();
					$(parent).find('.chart-empty-state').hide();
					this.assessment_line_chart.update(data);
				}
			}
		});
	}

	show_therapy_assessment_correlation() {
		let me = this;
		let assessment = frappe.ui.form.make_control({
			parent: $('.assessment-correlation-template-search'),
			df: {
				fieldtype: 'Link',
				options: 'Patient Assessment Template',
				fieldname: 'assessment',
				placeholder: __('Select Assessment Template'),
				only_select: true,
				change: () => {
					if (me.assessment != assessment.get_value() && assessment.get_value()) {
						me.assessment = assessment.get_value();
						me.render_therapy_assessment_correlation_chart();
					}
				}
			}
		});
		assessment.refresh();
		this.create_time_span_filters('render_therapy_assessment_correlation_chart', '.therapy-assessment-correlation');
	}

	render_therapy_assessment_correlation_chart(time_span='Last Month') {
		if (!this.assessment) return;

		frappe.xcall(
			'erpnext.healthcare.page.patient_progress.patient_progress.get_therapy_assessment_correlation_data', {
				patient: this.patient_id,
				assessment_template: this.assessment,
				time_span: time_span
			}
		).then(chart => {
			let data = {
				labels: chart.labels,
				datasets: chart.datasets,
				yMarkers: [
					{ label: 'Max Score', value: chart.max_score }
				],
			}
			let parent = '.therapy-assessment-correlation-chart';
			if (!chart.labels.length) {
				this.show_null_state(parent);
			} else {
				if (!this.correlation_chart) {
					this.correlation_chart = new frappe.Chart(parent, {
						type: 'axis-mixed',
						height: 300,
						data: data,
						axisOptions: {
							xIsSeries: 1
						}
					});
				} else {
					$(parent).find('.chart-container').show();
					$(parent).find('.chart-empty-state').hide();
					this.correlation_chart.update(data);
				}
			}
		});
	}

	show_assessment_parameter_progress() {
		let me = this;
		let parameter = frappe.ui.form.make_control({
			parent: $('.assessment-parameter-search'),
			df: {
				fieldtype: 'Link',
				options: 'Patient Assessment Parameter',
				fieldname: 'assessment',
				placeholder: __('Select Assessment Parameter'),
				only_select: true,
				change: () => {
					if (me.parameter != parameter.get_value() && parameter.get_value()) {
						me.parameter = parameter.get_value();
						me.render_assessment_parameter_progress_chart();
					}
				}
			}
		});
		parameter.refresh();
		this.create_time_span_filters('render_assessment_parameter_progress_chart', '.assessment-parameter-progress');
	}

	render_assessment_parameter_progress_chart(time_span='Last Month') {
		if (!this.parameter) return;

		frappe.xcall(
			'erpnext.healthcare.page.patient_progress.patient_progress.get_assessment_parameter_data', {
				patient: this.patient_id,
				parameter: this.parameter,
				time_span: time_span
			}
		).then(chart => {
			let data = {
				labels: chart.labels,
				datasets: chart.datasets
			}
			let parent = '.assessment-parameter-progress-chart';
			if (!chart.labels.length) {
				this.show_null_state(parent);
			} else {
				if (!this.parameter_chart) {
					this.parameter_chart = new frappe.Chart(parent, {
						type: 'line',
						height: 250,
						data: data,
						lineOptions: {
							regionFill: 1
						},
						axisOptions: {
							xIsSeries: 1
						},
						tooltipOptions: {
							formatTooltipY: d => d + '%'
						}
					});
				} else {
					$(parent).find('.chart-container').show();
					$(parent).find('.chart-empty-state').hide();
					this.parameter_chart.update(data);
				}
			}
		});
	}

	show_null_state(parent) {
		let null_state = $(parent).find('.chart-empty-state');
		if (null_state.length) {
			$(null_state).show();
		} else {
			null_state = $(
				`<div class="chart-empty-state text-muted text-center" style="margin-bottom: 20px;">${__(
					"No Data..."
				)}</div>`
			);
			$(parent).append(null_state);
		}
		$(parent).find('.chart-container').hide();
	}
}