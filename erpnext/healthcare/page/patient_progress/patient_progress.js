frappe.pages['patient-progress'].on_page_load = function(wrapper) {

	frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Patient Progress',
		single_column: true
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
		if (frappe.route_options) {
			patient.set_value(frappe.route_options.patient);
		}

		let route = frappe.get_route();
		this.patient_id = route[1];

		//validate if user
		if (route.length > 1) {
			frappe.db.exists('Patient', this.patient_id).then( exists => {
				if (exists) {
					this.make_patient_profile();
				} else {
					frappe.msgprint(__('Patient does not exist'));
				}
			});
		}
	}
}