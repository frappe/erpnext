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
	}

	make_patient_profile() {
		frappe.set_route('patient-progress', this.patient_id);
		this.page.set_title(__('Patient Progress'));
		this.main_section.empty().append(frappe.render_template('patient_progress'));
		this.render_patient_details();
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
			});
		});
	}

}