frappe.provide("erpnext.vehicles");

erpnext.vehicles.make_customer_vehicle_selector = function (frm, wrapper, vehicle_field, customer_field, party_type_field) {
	$(wrapper).empty();
	return new erpnext.vehicles.CustomerVehicleSelector(frm, wrapper, vehicle_field, customer_field, party_type_field);
};

erpnext.vehicles.CustomerVehicleSelector = Class.extend({
	init: function(frm, wrapper, vehicle_field, customer_field, party_type_field) {
		var me = this;

		me.frm = frm;

		me.vehicle_field = vehicle_field;
		me.customer_field = customer_field;
		me.party_type_field = party_type_field;

		me.wrapper = $(wrapper);
		me.wrapper.css('margin-bottom', '-10px');

		me.message_wrapper = $(`<div></div>`).appendTo(me.wrapper);

		me.grid_wrapper = $(`<div class='row'></div>`).appendTo(me.wrapper);
		me.vehicles_wrapper = $(`<div></div>`).appendTo(me.grid_wrapper);
		me.customers_wrapper = $(`<div></div>`).appendTo(me.grid_wrapper);

		me.vehicles = [];
		me.customers = [];

		if (me.frm.doc.__onload && me.frm.doc.__onload.customer_vehicle_selector_data) {
			me.vehicles = me.frm.doc.__onload.customer_vehicle_selector_data.vehicles || [];
			me.customers = me.frm.doc.__onload.customer_vehicle_selector_data.customers || [];
			me.render_selector();
		} else {
			me.load_and_render();
		}

		me.bind();
	},

	load_and_render: function () {
		var me = this;
		var customer = this.get_selected_customer();
		var vehicle = this.get_selected_vehicle();

		if (customer || vehicle) {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_log.vehicle_log.get_customer_vehicle_selector_data",
				args: {
					customer: customer,
					vehicle: vehicle,
				},
				callback: function (r) {
					if (r.message && !r.exc) {
						me.vehicles = r.message.vehicles;
						me.customers = r.message.customers;
						me.render_selector();
					}
				}
			});
		} else {
			me.vehicles = [];
			me.customers = [];
			me.render_selector();
		}
	},

	render_selector: function () {
		this.clear();

		var customer = this.get_selected_customer();
		var vehicle = this.get_selected_vehicle();

		if (customer) {
			if (this.vehicles && this.vehicles.length) {
				if (vehicle) {
					$(`<label class="control-label">${__("Vehicles")}</label>`).appendTo(this.vehicles_wrapper);
				}
				this.render_vehicles();
			} else {
				this.render_message(__("No Vehicles found in Customer history"));
			}
		}

		if (vehicle) {
			if (this.customers && this.customers.length) {
				if (customer) {
					$(`<label class="control-label">${__("Customers")}</label>`).appendTo(this.customers_wrapper);
				}
				this.render_customers();
			} else {
				this.render_message(__("No Customers found in Vehicle history"));
			}
		}

		if (customer && vehicle) {
			this.vehicles_wrapper.removeClass();
			this.vehicles_wrapper.addClass('col-md-9 col-sm-7');
			$('.customer-vehicle-col', this.vehicles_wrapper).addClass('col-md-6 col-sm-12');

			this.customers_wrapper.removeClass();
			this.customers_wrapper.addClass('col-md-3 col-sm-5');
			$('.customer-vehicle-col', this.customers_wrapper).addClass('col-md-12');
		} else {
			this.vehicles_wrapper.removeClass();
			this.vehicles_wrapper.addClass('col-md-12');
			$('.customer-vehicle-col', this.vehicles_wrapper).addClass('col-md-4 col-sm-6');

			this.customers_wrapper.removeClass();
			this.customers_wrapper.addClass('col-md-12');
			$('.customer-vehicle-col', this.customers_wrapper).addClass('col-md-4 col-sm-6');
		}

		if (!customer && !vehicle) {
			this.render_message(__("Select Customer or Vehicle to see Customer Vehicles from history"));
		}
	},

	render_vehicles: function() {
		var me = this;

		var container = $(`<div class='customer-vehicle-selector row'></div>`).appendTo(me.vehicles_wrapper);
		if (this.is_vehicle_editable()) {
			container.addClass('editable');
		}

		$.each(me.vehicles || [], function (i, vehicle) {
			var image_html = "";
			if (vehicle.image) {
				image_html = `<img src="${vehicle.image}" style="max-height: 60px;" alt="Vehicle Image">`;
			}

			var indicator_color = vehicle.is_current ? "blue" : "darkgrey";

			var selected_class = vehicle.name == me.get_selected_vehicle() ? "selected" : "";

			var vehicle_html = `
			<div class="customer-vehicle-col">
				<div class="card customer-vehicle-card ${selected_class}" data-vehicle="${vehicle.name}">

					<div class="card-header">
						<span class="indicator ${indicator_color} ellipsis">
							<b>${vehicle.item_name}</b>
						</span>
					</div>

					<div class="card-body">
						<div style="display: flex; align-items: center;">
							<div style="width: 79%;">
								<div><b>Reg #:</b> ${vehicle.license_plate || 'N/A'}</div>
								<div><b>Chassis #:</b> ${vehicle.chassis_no || 'N/A'}</div>
								<div><b>Engine #:</b> ${vehicle.engine_no || 'N/A'}</div>
								<div><b>Customer:</b> ${vehicle.customer_name || 'N/A'}</div>
							</div>
	
							<div style="width: 20%;">
								${image_html}
							</div>
						</div>
					</div>

				</div>
			</div>
			`;
			var $vehicle_html = $(vehicle_html).appendTo(container);
			if (me.is_master_document_view()) {
				$('.card', $vehicle_html).wrap(`<a href='/app/vehicle/${encodeURIComponent(vehicle.name)}'></a>`);
			}
		});
	},

	render_customers: function () {
		var me = this;

		var container = $(`<div class='customer-vehicle-selector row'></div>`).appendTo(me.customers_wrapper);
		if (this.is_customer_editable()) {
			container.addClass('editable');
		}

		$.each(me.customers || [], function (i, customer) {
			var indicator_color = customer.is_current ? "blue" : "darkgrey";

			var selected_class = customer.name == me.get_selected_customer() ? "selected" : "";

			var customer_html = `
			<div class="customer-vehicle-col">
				<div class="card customer-vehicle-card ${selected_class}" data-customer="${customer.name}">

					<div class="card-header">
						<span class="indicator ${indicator_color} ellipsis">
							<b>${customer.customer_name}</b>
						</span>
					</div>

					<div class="card-body">
						<div><b>CNIC/NTN:</b> ${customer.tax_cnic || customer.tax_id || 'N/A'}</div>
						<div><b>Contact #:</b> ${customer.mobile_no || customer.mobile_no_2 || customer.phone_no || 'N/A'}</div>
					</div>

				</div>
			</div>
			`;

			var $customer_html = $(customer_html).appendTo(container);
			if (me.is_master_document_view()) {
				$('.card', $customer_html).wrap(`<a href='/app/customer/${encodeURIComponent(customer.name)}'></a>`);
			}
		});
	},

	render_message: function (message) {
		$(`<div style="margin-bottom: 10px;">${message}</div>`).appendTo(this.message_wrapper);
	},

	clear: function () {
		this.vehicles_wrapper.empty();
		this.customers_wrapper.empty();
		this.message_wrapper.empty();
	},

	bind: function () {
		var me = this;

		if (me.is_vehicle_editable()) {
			me.vehicles_wrapper.on("click", ".customer-vehicle-card", function () {
				me.on_vehicle_click(this);
			});
		}

		if (me.is_customer_editable()) {
			me.customers_wrapper.on("click", ".customer-vehicle-card", function () {
				me.on_customer_click(this);
			});
		}
	},

	on_vehicle_click: function (el) {
		var vehicle = $(el).attr('data-vehicle');

		if (vehicle && this.is_vehicle_editable()) {
			this.frm.set_value(this.vehicle_field, vehicle);
		}
	},

	on_customer_click: function (el) {
		var customer = $(el).attr('data-customer');

		var tasks = [];
		if (customer && this.is_customer_editable()) {
			if (this.party_type_field) {
				tasks.push(() => this.frm.set_value(this.party_type_field, 'Customer'));
			}
			tasks.push(() => this.frm.set_value(this.customer_field, customer));
		}

		return frappe.run_serially(tasks);
	},

	get_selected_vehicle: function() {
		if (this.vehicle_field) {
			return this.frm.doc[this.vehicle_field];
		} else {
			return null;
		}
	},

	get_selected_customer: function () {
		if (this.party_type_field && this.frm.doc[this.party_type_field] != 'Customer') {
			return null;
		} else if (this.customer_field) {
			return this.frm.doc[this.customer_field];
		} else {
			return null;
		}
	},

	is_vehicle_editable: function () {
		if (!this.vehicle_field || this.vehicle_field == "name") {
			return false;
		} else {
			return this.frm.fields_dict[this.vehicle_field] && this.frm.fields_dict[this.vehicle_field].disp_status == "Write";
		}
	},

	is_customer_editable: function () {
		if (!this.customer_field || this.customer_field == "name") {
			return false;
		} else {
			return this.frm.fields_dict[this.customer_field] && this.frm.fields_dict[this.customer_field].disp_status == "Write";
		}
	},

	is_master_document_view: function () {
		if (this.vehicle_field == "name" && !this.customer_field) {
			return true;
		} else if (this.customer_field == "name" && !this.vehicle_field) {
			return true;
		} else {
			return false;
		}
	}
});
