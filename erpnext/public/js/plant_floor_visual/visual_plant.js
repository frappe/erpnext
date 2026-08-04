class VisualPlantFloor {
	constructor({ wrapper, skip_filters = false, plant_floor = null }, page = null) {
		this.wrapper = wrapper;
		this.plant_floor = plant_floor;
		this.skip_filters = skip_filters;

		this.make();
		if (!this.skip_filters) {
			this.page = page;
			this.add_filter();
			this.prepare_menu();
		}
	}

	make() {
		this.wrapper.append(`
			<div class="plant-floor">
				<div class="plant-floor-filter">
				</div>
				<div class="plant-floor-container col-sm-12">
				</div>
			</div>
		`);

		if (!this.skip_filters) {
			this.filter_wrapper = this.wrapper.find(".plant-floor-filter");
			this.visualization_wrapper = this.wrapper.find(".plant-floor-visualization");
		} else if (this.plant_floor) {
			this.wrapper.find(".plant-floor").css("border", "none");
			this.prepare_data();
		}
	}

	prepare_data() {
		frappe.call({
			method: "erpnext.manufacturing.doctype.workstation.workstation.get_workstations",
			args: {
				plant_floor: this.plant_floor,
			},
			callback: (r) => {
				this.workstations = r.message;
				this.render_workstations();
			},
		});
	}

	add_filter() {
		this.plant_floor = frappe.ui.form.make_control({
			df: {
				fieldtype: "Link",
				options: "Plant Floor",
				fieldname: "plant_floor",
				label: __("Plant Floor"),
				reqd: 1,
				onchange: () => {
					this.render_plant_visualization();
				},
			},
			parent: this.filter_wrapper,
			render_input: true,
		});

		this.plant_floor.$wrapper.addClass("form-column col-sm-2");

		this.workstation_type = frappe.ui.form.make_control({
			df: {
				fieldtype: "Link",
				options: "Workstation Type",
				fieldname: "workstation_type",
				label: __("Machine Type"),
				onchange: () => {
					this.render_plant_visualization();
				},
			},
			parent: this.filter_wrapper,
			render_input: true,
		});

		this.workstation_type.$wrapper.addClass("form-column col-sm-2");

		this.workstation = frappe.ui.form.make_control({
			df: {
				fieldtype: "Link",
				options: "Workstation",
				fieldname: "workstation",
				label: __("Machine"),
				onchange: () => {
					this.render_plant_visualization();
				},
				get_query: () => {
					if (this.workstation_type.get_value()) {
						return {
							filters: {
								workstation_type: this.workstation_type.get_value() || "",
							},
						};
					}
				},
			},
			parent: this.filter_wrapper,
			render_input: true,
		});

		this.workstation.$wrapper.addClass("form-column col-sm-2");

		this.workstation_status = frappe.ui.form.make_control({
			df: {
				fieldtype: "Select",
				options: "\nProduction\nOff\nIdle\nProblem\nMaintenance\nSetup",
				fieldname: "workstation_status",
				label: __("Status"),
				onchange: () => {
					this.render_plant_visualization();
				},
			},
			parent: this.filter_wrapper,
			render_input: true,
		});
	}

	render_plant_visualization() {
		let plant_floor = this.plant_floor.get_value();

		if (plant_floor) {
			frappe.call({
				method: "erpnext.manufacturing.doctype.workstation.workstation.get_workstations",
				args: {
					plant_floor: plant_floor,
					workstation_type: this.workstation_type.get_value(),
					workstation: this.workstation.get_value(),
					workstation_status: this.workstation_status.get_value(),
				},
				callback: (r) => {
					this.workstations = r.message;
					this.render_workstations();
				},
			});
		}
	}

	render_workstations() {
		this.wrapper.find(".plant-floor-container").empty();
		let template = frappe.render_template("visual_plant_floor_template", {
			workstations: this.workstations,
		});

		$(template).appendTo(this.wrapper.find(".plant-floor-container"));
	}

	prepare_menu() {
		this.page.add_menu_item(__("Refresh"), () => {
			this.render_plant_visualization();
		});
	}
}

frappe.ui.VisualPlantFloor = VisualPlantFloor;
