// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Workstation", {
	set_illustration_image(frm) {
		let status_image_field = frm.doc.status == "Production" ? frm.doc.on_status_image : frm.doc.off_status_image;
		if (status_image_field) {
			frm.sidebar.image_wrapper.find(".sidebar-image").attr("src", status_image_field);
		}
	},

	refresh(frm) {
		frm.trigger("set_illustration_image");
		frm.trigger("prepapre_dashboard");
	},

	prepapre_dashboard(frm) {
		let $parent = $(frm.fields_dict["workstation_dashboard"].wrapper);
		$parent.empty();

		let workstation_dashboard = new WorkstationDashboard({
			wrapper: $parent,
			frm: frm
		});
	},

	onload(frm) {
		if(frm.is_new())
		{
			frappe.call({
				type:"GET",
				method:"erpnext.manufacturing.doctype.workstation.workstation.get_default_holiday_list",
				callback: function(r) {
					if(!r.exe && r.message){
						cur_frm.set_value("holiday_list", r.message);
					}
				}
			})
		}
	},

	workstation_type(frm) {
		if (frm.doc.workstation_type) {
			frm.call({
				method: "set_data_based_on_workstation_type",
				doc: frm.doc,
				callback: function(r) {
					frm.refresh_fields();
				}
			})
		}
	}
});

frappe.tour['Workstation'] = [
	{
		fieldname: "workstation_name",
		title: "Workstation Name",
		description: __("You can set it as a machine name or operation type. For example, stiching machine 12")
	},
	{
		fieldname: "production_capacity",
		title: "Production Capacity",
		description: __("No. of parallel job cards which can be allowed on this workstation. Example: 2 would mean this workstation can process production for two Work Orders at a time.")
	},
	{
		fieldname: "holiday_list",
		title: "Holiday List",
		description: __("A Holiday List can be added to exclude counting these days for the Workstation.")
	},
	{
		fieldname: "working_hours",
		title: "Working Hours",
		description: __("Under Working Hours table, you can add start and end times for a Workstation. For example, a Workstation may be active from 9 am to 1 pm, then 2 pm to 5 pm. You can also specify the working hours based on shifts. While scheduling a Work Order, the system will check for the availability of the Workstation based on the working hours specified.")
	},


];


class WorkstationDashboard {
	constructor({ wrapper, frm }) {
		this.$wrapper = $(wrapper);
		this.frm = frm;

		this.prepapre_dashboard();
	}

	prepapre_dashboard() {
		frappe.call({
			method: "erpnext.manufacturing.doctype.workstation.workstation.get_job_cards",
			args: {
				workstation: this.frm.doc.name
			},
			callback: (r) => {
				if (r.message) {
					this.render_job_cards(r.message);
				}
			}
		});
	}

	render_job_cards(job_cards) {
		let template  = frappe.render_template("workstation_job_card", {
			data: job_cards
		});

		this.$wrapper.html(template);
		this.$wrapper.find(".collapse-indicator-job").on("click", (e) => {
			$(e.currentTarget).closest(".form-dashboard-section").find(".section-body-job-card").toggleClass("hide")
			if ($(e.currentTarget).closest(".form-dashboard-section").find(".section-body-job-card").hasClass("hide"))
				$(e.currentTarget).html(frappe.utils.icon("es-line-down", "sm", "mb-1"))
			else
				$(e.currentTarget).html(frappe.utils.icon("es-line-up", "sm", "mb-1"))
		});
	}
}