frappe.pages['patient-progress'].on_page_load = function(wrapper) {

	frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Patient Progress')
	});

	let patient_progress = new PatientProgress(wrapper);
	$(wrapper).bind('show', ()=> {
		patient_progress.show();
	});
}

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
				change: () => {
					me.patient_id = ''
					if (me.patient_id != patient.get_value() && patient.get_value()) {
						me.start = 0;
						me.patient_id = patient.get_value();
						me.make_patient_profile();
					}
				}
			},
			only_select: true,
		});
		patient.refresh();

		if (frappe.route_options) {
			patient.set_value(frappe.route_options.patient);
			this.patient_id = frappe.route_options.patient;
		}

		this.sidebar.find('[data-fieldname="patient"]').append('<div class="patient-info"></div>');
		this.empty = $(
			`<div class="chart-loading-state text-muted">${__(
				"No Data..."
			)}</div>`
		);
	}

	make_patient_profile() {
		frappe.set_route('patient-progress', this.patient_id);
		this.page.set_title(__('Patient Progress'));
		this.main_section.empty().append(frappe.render_template('patient_progress'));
		this.render_patient_details();
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
			name: this.patient_id,

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
				label: 'Type',
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

	show_therapy_progress() {
		let me = this;
		let therapy_type = frappe.ui.form.make_control({
			parent: $('.therapy-type-search'),
			df: {
				fieldtype: 'Link',
				options: 'Therapy Type',
				fieldname: 'therapy_type',
				placeholder: __('Select Therapy Type'),
				change: () => {
					if (me.therapy_type != therapy_type.get_value() && therapy_type.get_value()) {
						me.therapy_type = therapy_type.get_value();
						me.render_therapy_progress_chart(me.therapy_type);
					}
				}
			},
			only_select: true
		});
		therapy_type.refresh();
	}

	render_therapy_progress_chart(therapy_type) {
		frappe.xcall(
			'erpnext.healthcare.page.patient_progress.patient_progress.get_therapy_progress_data', {
				patient: this.patient_id,
				therapy_type: therapy_type
			}
		).then(chart => {
			let data = {
				labels: chart.labels,
				datasets: chart.datasets
			}
			if (!this.line_chart) {
				this.wrapper.find('.therapy-progress-line-chart').show();
				this.therapy_line_chart = new frappe.Chart('.therapy-progress-line-chart', {
					title: __('Therapy Progress'),
					type: 'axis-mixed',
					height: 250,
					data: data,
					lineOptions: {
						regionFill: 1,
					},
					axisOptions: {
						xIsSeries: 1
					},
				});
			} else {
				if (data.labels.length) {
					this.wrapper.find('.therapy-progress-line-chart').show();
					this.therapy_line_chart.update(data);
				} else {
					this.wrapper.find('.therapy-progress-line-chart').hide();
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
				change: () => {
					if (me.assessment_template != assessment_template.get_value() && assessment_template.get_value()) {
						me.assessment_template = assessment_template.get_value();
						me.render_assessment_result_chart(me.assessment_template);
					}
				}
			},
			only_select: true
		});
		assessment_template.refresh();
	}

	render_assessment_result_chart(assessment_template) {
		frappe.xcall(
			'erpnext.healthcare.page.patient_progress.patient_progress.get_patient_assessment_data', {
				patient: this.patient_id,
				assessment_template: assessment_template
			}
		).then(chart => {
			let data = {
				labels: chart.labels,
				datasets: chart.datasets
			}
			if (!this.assessment_line_chart) {
				this.wrapper.find('.assessment-results-line-chart').show();
				this.assessment_line_chart = new frappe.Chart('.assessment-results-line-chart', {
					title: __('Assessment Results'),
					type: 'axis-mixed',
					height: 250,
					data: data,
					lineOptions: {
						regionFill: 1,
					},
					axisOptions: {
						xIsSeries: 1
					},
				});
			} else {
				if (data.labels.length) {
					this.wrapper.find('.assessment-results-line-chart').show();
					this.assessment_line_chart.update(data);
					this.empty.hide();
				} else {
					this.wrapper.find('.assessment-results-line-chart').hide();
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
				change: () => {
					if (me.assessment != assessment.get_value() && assessment.get_value()) {
						me.assessment = assessment.get_value();
						me.render_therapy_assessment_correlation_chart(me.assessment);
					}
				}
			},
			only_select: true
		});
		assessment.refresh();
	}

	render_therapy_assessment_correlation_chart(assessment) {
		frappe.xcall(
			'erpnext.healthcare.page.patient_progress.patient_progress.get_therapy_assessment_correlation_data', {
				patient: this.patient_id,
				assessment_template: assessment
			}
		).then(chart => {
			let data = {
				labels: chart.labels,
				datasets: chart.datasets
			}
			if (!this.correlation_chart) {
				this.wrapper.find('.therapy-assessment-correlation-line-chart').show();
				this.correlation_chart = new frappe.Chart('.therapy-assessment-correlation-chart', {
					title: __('Correlation'),
					type: 'axis-mixed',
					height: 300,
					data: data,
					axisOptions: {
						xIsSeries: 1
					}
				});
			} else {
				if (data.labels.length) {
					this.wrapper.find('.therapy-assessment-correlation-chart').show();
					this.correlation_chart.update(data);
				} else {
					this.wrapper.find('.therapy-assessment-correlation-chart').hide();
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
				change: () => {
					if (me.parameter != parameter.get_value() && parameter.get_value()) {
						me.parameter = parameter.get_value();
						me.render_assessment_parameter_progress_chart(me.parameter);
					}
				}
			},
			only_select: true
		});
		parameter.refresh();
	}

	render_assessment_parameter_progress_chart(parameter) {
		frappe.xcall(
			'erpnext.healthcare.page.patient_progress.patient_progress.get_assessment_parameter_data', {
				patient: this.patient_id,
				parameter: parameter
			}
		).then(chart => {
			let data = {
				labels: chart.labels,
				datasets: chart.datasets
			}
			if (!this.parameter_chart) {
				this.wrapper.find('.assessment-parameter-progress-chart').show();
				this.parameter_chart = new frappe.Chart('.assessment-parameter-progress-chart', {
					title: __('Assessment Parameter Progress'),
					type: 'line',
					height: 250,
					data: data,
					axisOptions: {
						xIsSeries: 1
					}
				});
			} else {
				if (data.labels.length) {
					this.wrapper.find('.assessment-parameter-progress-chart').show();
					this.parameter_chart.update(data);
				} else {
					this.wrapper.find('.assessment-parameter-progress-chart').hide();
				}
			}
		});
	}
}