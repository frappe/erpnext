// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.provide("erpnext.vehicles");

erpnext.vehicles.VehicleBookingOrder = class VehicleBookingOrder extends erpnext.vehicles.VehicleBookingController {
	setup() {
		this.frm.custom_make_buttons = {
			'Vehicle Booking Payment': 'Customer Payment',
			'Vehicle Receipt': 'Receive Vehicle',
			'Vehicle Delivery': 'Deliver Vehicle',
			'Vehicle Invoice': 'Receive Invoice',
			'Vehicle Invoice Delivery': 'Deliver Invoice',
			'Vehicle Transfer Letter': 'Transfer Letter',
			'Vehicle Registration Order': 'Registration Order',
			'Vehicle Invoice Movement': 'Invoice Movement',
			'Project': 'Create PDI Repair Order',
		}
	}

	refresh() {
		super.refresh();
		this.set_customer_is_company_label();
		this.set_dynamic_link();
		this.setup_buttons();
		this.setup_dashboard();
	}

	setup_queries() {
		super.setup_queries();

		var me = this;

		if (this.frm.fields_dict.allocation_period) {
			this.frm.set_query("allocation_period", function () {
				var filters = {
					item_code: me.frm.doc.item_code,
					supplier: me.frm.doc.supplier,
					vehicle_color: me.frm.doc.color_1
				}
				if (me.frm.doc.delivery_period) {
					filters['delivery_period'] = me.frm.doc.delivery_period;
				}
				return erpnext.queries.vehicle_allocation_period('allocation_period', filters);
			});
		}

		if (this.frm.fields_dict.vehicle_allocation) {
			this.frm.set_query("vehicle_allocation", () => me.allocation_query());
		}
	}

	setup_route_options() {
		super.setup_route_options();

		var allocation_field = this.frm.get_docfield("vehicle_allocation");
		if (allocation_field) {
			allocation_field.get_route_options_for_new_doc = () => this.allocation_route_options();
		}
	}

	allocation_route_options(dialog) {
		return {
			"company": this.frm.doc.company,
			"item_code": this.frm.doc.item_code,
			"item_name": this.frm.doc.item_name,
			"supplier": this.frm.doc.supplier,
			"allocation_period": dialog ? dialog.get_value('delivery_period') : this.frm.doc.allocation_period || this.frm.doc.delivery_period,
			"delivery_period": dialog ? dialog.get_value('delivery_period') : this.frm.doc.delivery_period
		}
	}

	allocation_query(ignore_allocation_period, dialog) {
		var filters = {
			item_code: this.frm.doc.item_code,
			supplier: this.frm.doc.supplier,
			vehicle_color: this.frm.doc.color_1,
			is_booked: 0
		}
		if (!ignore_allocation_period && this.frm.doc.allocation_period) {
			filters['allocation_period'] = this.frm.doc.allocation_period;
		}

		if (dialog) {
			var delivery_period = dialog.get_value('delivery_period');
			if (delivery_period) {
				filters['delivery_period'] = dialog.get_value('delivery_period');
			}
		} else {
			if (this.frm.doc.delivery_period) {
				filters['delivery_period'] = this.frm.doc.delivery_period;
			}
		}

		return {
			query: "erpnext.controllers.queries.vehicle_allocation_query",
			filters: filters
		};
	}

	setup_buttons() {
		// Customer Payment Button (allowed on draft too)
		if (this.frm.doc.docstatus < 2) {
			if (flt(this.frm.doc.customer_outstanding) > 0) {
				this.frm.add_custom_button(__('Customer Payment'),
					() => this.make_payment_entry(this.frm.doc.customer_is_company ? 'Company' : 'Customer'), __('Payment'));
			}
		}

		if (this.frm.doc.docstatus === 1) {
			var unpaid = flt(this.frm.doc.customer_outstanding) > 0 || flt(this.frm.doc.supplier_outstanding) > 0;

			// Supplier Payment Button
			if (flt(this.frm.doc.supplier_outstanding) > 0) {
				this.frm.add_custom_button(__('Supplier Payment'), () => this.make_payment_entry('Supplier'), __('Payment'));
			}

			// Registration Order button
			if (this.frm.doc.registration_status == "Not Ordered") {
				this.frm.add_custom_button(__('Registration Order'), () => this.make_next_document('Vehicle Registration Order'),
					__("Registration"));
			}

			// Receive/Deliver Vehicle and Invoice
			if (this.frm.doc.vehicle) {
				// Vehicle Delivery/Receipt buttons
				if (this.frm.doc.delivery_status === "Not Received") {
					if (this.can_change('vehicle_receipt')) {
						this.frm.add_custom_button(__('Receive Vehicle'), () => this.make_next_document('Vehicle Receipt'));
					}
				} else if (this.frm.doc.delivery_status === "In Stock") {
					if (this.can_change('vehicle_delivery')) {
						this.frm.add_custom_button(__('Deliver Vehicle'), () => this.make_next_document('Vehicle Delivery'));
					}
				}

				// Invoice Delivery/Receipt buttons
				if (this.frm.doc.invoice_status === "Not Received") {
					if (this.can_change('invoice_receipt')) {
						this.frm.add_custom_button(__('Receive Invoice'), () => this.make_next_document('Vehicle Invoice'));
					}
				} else if (this.frm.doc.invoice_status === "In Hand") {
					if (this.can_change('invoice_delivery')) {
						this.frm.add_custom_button(__('Deliver Invoice'), () => this.make_next_document('Vehicle Invoice Delivery'));
					}
				}

				// Transfer Letter button
				if (!this.frm.doc.transfer_customer) {
					if (this.can_change('vehicle_transfer')) {
						this.frm.add_custom_button(__('Transfer Letter'), () => this.make_next_document('Vehicle Transfer Letter'),
							__("Registration"));
					}
				}

				// PDI Buttons
				if (["In Stock", "Delivered"].includes(this.frm.doc.delivery_status) && !['In Process', 'Done'].includes(this.frm.doc.pdi_status)) {
					if (frappe.model.can_create("Project")) {
						this.frm.add_custom_button(__('Create PDI Repair Order'), () => this.make_next_document('Project'),
							__("Service"));
					}

					if (this.can_change('vehicle_delivery')) {
						var pdi_request_label = this.frm.doc.pdi_requested ? __('Cancel PDI Request') : __('Request PDI');
						this.frm.add_custom_button(pdi_request_label, () => this.change_pdi_requested(),
							__("Service"));
					}
				}

				// Return Vehicle buttons
				if (this.frm.doc.delivery_status === "In Stock") {
					if (this.can_change('vehicle_receipt')) {
						this.frm.add_custom_button(__('Return Vehicle to Supplier'), () => this.make_next_document('Vehicle Receipt Return'),
							__("Return"));
					}
				} else if (this.frm.doc.delivery_status === "Delivered") {
					if (this.can_change('vehicle_delivery')) {
						this.frm.add_custom_button(__('Return Vehicle from Customer'), () => this.make_next_document('Vehicle Delivery Return'),
							__("Return"));
					}
				}
			}

			// Change / Select labels
			var select_vehicle_label = this.frm.doc.vehicle ? "Change Vehicle (Unit)" : "Select Vehicle (Unit)";
			var select_allocation_label = this.frm.doc.vehicle_allocation ? "Change Vehicle Allocation" : "Select Allocation";
			var select_delivery_period_label = this.frm.doc.delivery_period ? "Change Delivery Period" : "Select Delivery Period";
			var change_priority_label = cint(this.frm.doc.priority) ? "Mark as Normal Priority" : "Mark as High Priority";
			var change_cancellation_label = cint(this.frm.doc.status === "Cancelled Booking") ? "Re-Open Booking" : "Cancel Booking";
			var change_outstation_delivery_label = cint(this.frm.doc.outstation_delivery) ? "Disable Outstation Delivery" : "Enable Outstation Delivery";

			// Status Buttons
			if (this.can_change('cancellation')) {
				this.frm.add_custom_button(__(change_cancellation_label), () => this.change_cancellation(),
					__("Status"));
			}

			// Notification Buttons
			this.setup_notification_buttons();

			// Change Buttons
			if (this.can_change('customer_details')) {
				this.frm.add_custom_button(__("Update Customer Details"), () => this.change_customer_details(),
					__("Change"));
			}

			if (this.can_change('allocation')) {
				this.frm.add_custom_button(__(select_allocation_label), () => this.change_allocation(),
					this.frm.doc.vehicle_allocation ? __("Change") : null);
			}

			if (this.can_change('delivery_period')) {
				this.frm.add_custom_button(__(select_delivery_period_label), () => this.change_delivery_period(),
					this.frm.doc.delivery_period ? __("Change") : null);
			}

			if (this.can_change('outstation_delivery')) {
				this.frm.add_custom_button(__(change_outstation_delivery_label), () => this.change_outstation_delivery(),
					__("Change"));
			}

			if (this.can_change('color')) {
				this.frm.add_custom_button(__("Change Vehicle Color"), () => this.change_color(),
					__("Change"));
			}

			if (this.can_change('vehicle')) {
				this.frm.add_custom_button(__(select_vehicle_label), () => this.change_vehicle(),
					this.frm.doc.vehicle ? __("Change") : null);
			}

			if (this.can_change('payment_adjustment')) {
				this.frm.add_custom_button(__("Change Payment Adjustment"), () => this.change_payment_adjustment(),
					__("Change"));
			}

			if (this.can_change('vehicle_price')) {
				this.frm.add_custom_button(__("Change Vehicle Price"), () => this.change_vehicle_price(),
					__("Change"));
			}

			if (this.can_change('priority')) {
				this.frm.add_custom_button(__(change_priority_label), () => this.change_priority(),
					__("Change"));
			}

			if (this.can_change('item')) {
				this.frm.add_custom_button(__("Change Vehicle Item (Variant)"), () => this.change_item(),
					__("Change"));
			}

			if (this.frm.doc.vehicle_allocation_required && !this.frm.doc.vehicle_allocation) {
				this.frm.custom_buttons[__(select_allocation_label)] && this.frm.custom_buttons[__(select_allocation_label)].addClass('btn-primary');
			}

			if (unpaid) {
				this.frm.page.set_inner_btn_group_as_primary(__('Payment'));

			} else if (!this.frm.doc.vehicle) {
				this.frm.custom_buttons[__(select_vehicle_label)] && this.frm.custom_buttons[__(select_vehicle_label)].addClass('btn-primary');

			} else if (this.frm.doc.status === "To Receive Vehicle") {
				this.frm.custom_buttons[__('Receive Vehicle')] && this.frm.custom_buttons[__('Receive Vehicle')].addClass('btn-primary');

			} else if (this.frm.doc.status === "To Receive Invoice") {
				this.frm.custom_buttons[__('Receive Invoice')] && this.frm.custom_buttons[__('Receive Invoice')].addClass('btn-primary');

			} else if (this.frm.doc.status === "To Deliver Vehicle") {
				this.frm.custom_buttons[__('Deliver Vehicle')] && this.frm.custom_buttons[__('Deliver Vehicle')].addClass('btn-primary');

			} else if (this.frm.doc.status === "To Deliver Invoice") {
				this.frm.custom_buttons[__('Deliver Invoice')] && this.frm.custom_buttons[__('Deliver Invoice')].addClass('btn-primary');
			}
		}
	}

	setup_dashboard() {
		if (this.frm.doc.docstatus !== 1) {
			return;
		}

		var me = this;
		var company_currency = erpnext.get_currency(me.frm.doc.company);

		me.frm.dashboard.stats_area.removeClass('hidden');
		me.frm.dashboard.stats_area_row.addClass('flex');
		me.frm.dashboard.stats_area_row.css('flex-wrap', 'wrap');

		// Payment Status
		var customer_outstanding_color = me.frm.doc.customer_outstanding ? "orange" : "green";

		var supplier_outstanding_color;
		if (!me.frm.doc.supplier_outstanding) {
			supplier_outstanding_color = "green";
		} else if (me.frm.doc.supplier_outstanding == me.frm.doc.customer_outstanding) {
			supplier_outstanding_color = "blue";
		} else {
			supplier_outstanding_color = "orange";
		}

		var payment_adjustment_color;
		if (!me.frm.doc.payment_adjustment) {
			payment_adjustment_color = 'grey';
		} else if (me.frm.doc.payment_adjustment > 0) {
			payment_adjustment_color = 'blue';
		} else {
			payment_adjustment_color = 'orange';
		}

		me.add_indicator_section(__("Payment"), [
			{
				contents: __('Invoice Total: {0}', [format_currency(me.frm.doc.invoice_total, company_currency)]),
				indicator: 'blue'
			},
			{
				contents: __('Payment Adjustment: {0}', [format_currency(me.frm.doc.payment_adjustment, company_currency)]),
				indicator: payment_adjustment_color
			},
			{
				contents: __('Customer Outstanding: {0}', [format_currency(me.frm.doc.customer_outstanding, company_currency)]),
				indicator: customer_outstanding_color
			},
			{
				contents: __('Supplier Outstanding: {0}', [format_currency(me.frm.doc.supplier_outstanding, company_currency)]),
				indicator: supplier_outstanding_color
			},
		]);

		// Fulfilment Status
		var delivery_status_color;
		if (me.frm.doc.delivery_status == "Not Received") {
			delivery_status_color = "blue";
		} else if (me.frm.doc.delivery_status == "In Stock") {
			delivery_status_color = "orange";
		} else if (me.frm.doc.delivery_status == "Delivered") {
			delivery_status_color = "green";
		} else if (me.frm.doc.delivery_status == "Not Applicable") {
			delivery_status_color = "grey";
		}

		var overdue_warning = ["Not Received", "In Stock"].includes(me.frm.doc.delivery_status) && cint(me.frm.doc.delivery_overdue);
		if (overdue_warning) {
			delivery_status_color = "red";
		}

		var invoice_status_color;
		if (me.frm.doc.invoice_status == "Not Received") {
			invoice_status_color = "blue";
		} else if (me.frm.doc.invoice_status == "In Hand") {
			invoice_status_color = "orange";
		} else if (me.frm.doc.invoice_status == "Issued") {
			invoice_status_color = "purple";
		} else if (me.frm.doc.invoice_status == "Delivered") {
			invoice_status_color = "green";
		}

		var registration_status_color;
		if (me.frm.doc.registration_status == "Not Ordered") {
			registration_status_color = "grey";
		} else if (me.frm.doc.registration_status == "Ordered") {
			registration_status_color = "blue";
		} else if (me.frm.doc.registration_status == "In Process") {
			registration_status_color = "orange";
		} else if (me.frm.doc.registration_status == "Registered") {
			registration_status_color = "green";
		}

		var pdi_status_color;
		if (me.frm.doc.pdi_status == "Not Requested") {
			pdi_status_color = "grey";
		} else if (me.frm.doc.pdi_status == "Requested") {
			pdi_status_color = "blue";
		} else if (me.frm.doc.pdi_status == "In Process") {
			pdi_status_color = "orange";
		} else if (me.frm.doc.pdi_status == "Done") {
			pdi_status_color = "green";
		}

		var fulfilment_items = [
			{
				contents: __('Priority: {0}', [cint(me.frm.doc.priority) ? 'High' : 'Normal']),
				indicator: cint(me.frm.doc.priority) ? 'red' : 'blue'
			},
			{
				contents: __('Delivery Status: {0}{1}', [me.frm.doc.delivery_status,
					overdue_warning ? __(" (Overdue)") : ""]),
				indicator: delivery_status_color
			},
		];

		if (me.frm.doc.__onload && me.frm.doc.__onload.vehicle_warehouse_name) {
			fulfilment_items.push({
				contents: __('Location: {0}', [me.frm.doc.__onload.vehicle_warehouse_name]),
				indicator: 'lightblue'
			});
		}

		fulfilment_items.push(...[
			{
				contents: __('Invoice Status: {0}{1}', [me.frm.doc.invoice_status,
					me.frm.doc.invoice_status == "Issued" && me.frm.doc.invoice_issued_for ? " For " + me.frm.doc.invoice_issued_for : ""]),
				indicator: invoice_status_color
			},
			{
				contents: __('Registration Status: {0}', [me.frm.doc.registration_status]),
				indicator: registration_status_color
			},
			{
				contents: __('PDI Status: {0}', [me.frm.doc.pdi_status]),
				indicator: pdi_status_color
			},
		]);

		me.add_indicator_section(__("Fulfilment"), fulfilment_items);

		// Notification Status
		var booking_confirmation_count = frappe.get_notification_count(me.frm, 'Booking Confirmation', 'SMS');
		var booking_confirmation_color = booking_confirmation_count ? "green"
			: this.can_notify('Booking Confirmation') ? "yellow" : "grey";
		var booking_confirmation_status = booking_confirmation_count ? __("{0} SMS", [booking_confirmation_count])
			: __("Not Sent");

		var balance_payment_count = frappe.get_notification_count(me.frm, 'Balance Payment Due', 'SMS');
		var balance_payment_color = balance_payment_count ? "green"
			: this.can_notify('Balance Payment Due') ? "yellow" : "grey";
		var balance_payment_status = balance_payment_count ? __("{0} SMS", [balance_payment_count])
			: __("Not Sent");

		var payment_confirmation_count = frappe.get_notification_count(me.frm, 'Balance Payment Confirmation', 'SMS');
		var payment_confirmation_color = payment_confirmation_count ? "green"
			: this.can_notify('Balance Payment Confirmation') ? "yellow" : "grey";
		var payment_confirmation_status = payment_confirmation_count ? __("{0} SMS", [payment_confirmation_count])
			: __("Not Sent");

		var ready_for_delivery_count = frappe.get_notification_count(me.frm, 'Ready For Delivery', 'SMS');
		var ready_for_delivery_color = ready_for_delivery_count ? "green"
			: this.can_notify('Ready For Delivery') ? "yellow" : "grey";
		var ready_for_delivery_status = ready_for_delivery_count ? __("{0} SMS", [ready_for_delivery_count])
			: __("Not Sent");

		var congratulations_count = frappe.get_notification_count(me.frm, 'Congratulations', 'SMS');
		var congratulations_color = congratulations_count ? "green"
			: this.can_notify('Congratulations') ? "yellow" : "grey";
		var congratulations_status = congratulations_count ? __("{0} SMS", [congratulations_count])
			: __("Not Sent");

		var booking_cancellation_count = frappe.get_notification_count(me.frm, 'Booking Cancellation', 'SMS');
		var booking_cancellation_color = booking_cancellation_count ? "green"
			: this.can_notify('Booking Cancellation') ? "yellow" : "grey";
		var booking_cancellation_status = booking_cancellation_count ? __("{0} SMS", [booking_cancellation_count])
			: __("Not Sent");

		var indicator_items = [
			{
				contents: __('Booking Confirmation: {0}', [booking_confirmation_status]),
				indicator: booking_confirmation_color
			},
			{
				contents: __('Balance Payment Due: {0}', [balance_payment_status]),
				indicator: balance_payment_color
			},
			{
				contents: __('Balance Payment Confirmation: {0}', [payment_confirmation_status]),
				indicator: payment_confirmation_color
			},
			{
				contents: __('Ready For Delivery: {0}', [ready_for_delivery_status]),
				indicator: ready_for_delivery_color
			},
			{
				contents: __('Congratulations: {0}', [congratulations_status]),
				indicator: congratulations_color
			},
		];

		if (this.frm.doc.status == "Cancelled Booking") {
			indicator_items.push({
				contents: __('Booking Cancellation: {0}', [booking_cancellation_status]),
				indicator: booking_cancellation_color
			});
		}

		me.add_indicator_section(__("Notification"), indicator_items);
	}

	add_indicator_section(title, items) {
		var items_html = '';
		$.each(items || [], function (i, d) {
			items_html += `<div class="badge-link small">
				<span class="indicator ${d.indicator}">${d.contents}</span>
			</div>`
		});

		var html = $(`<div class="flex-column col-sm-4 col-md-4">
			<div><h6>${title}</h6></div>
			${items_html}
		</div>`);

		html.appendTo(this.frm.dashboard.stats_area_row);

		return html
	}

	setup_notification_buttons() {
		var me = this;
		if(this.frm.doc.docstatus === 1) {
			if (this.can_notify("Booking Cancellation")) {
				var booking_cancellation_count = frappe.get_notification_count(this.frm, 'Booking Cancellation', 'SMS');
				let label = __("Booking Cancellation{0}", [booking_cancellation_count ? " (Resend)" : ""]);
				this.frm.add_custom_button(label, () => this.send_sms('Booking Cancellation'),
					__("Notify"));
			}

			if (this.can_notify("Booking Confirmation")) {
				var booking_confirmation_count = frappe.get_notification_count(this.frm, 'Booking Confirmation', 'SMS');
				let label = __("Booking Confirmation{0}", [booking_confirmation_count ? " (Resend)" : ""]);
				this.frm.add_custom_button(label, () => this.send_sms('Booking Confirmation'),
					__("Notify"));
			}

			if (this.can_notify("Balance Payment Due")) {
				var balance_payment_count = frappe.get_notification_count(this.frm, 'Balance Payment Due', 'SMS');
				let label = __("Balance Payment Due{0}", [balance_payment_count ? " (Resend)" : ""]);
				this.frm.add_custom_button(label, () => this.send_sms('Balance Payment Due'),
					__("Notify"));
			}

			if (this.can_notify("Ready For Delivery")) {
				var ready_for_delivery_count = frappe.get_notification_count(this.frm, 'Ready For Delivery', 'SMS');
				let label = __("Ready For Delivery{0}", [ready_for_delivery_count ? " (Resend)" : ""]);
				this.frm.add_custom_button(label, () => this.send_sms('Ready For Delivery'),
					__("Notify"));
			}

			if (this.can_notify("Congratulations")) {
				var congratulations_count = frappe.get_notification_count(this.frm, 'Congratulations', 'SMS');
				let label = __("Congratulations{0}", [congratulations_count ? " (Resend)" : ""]);
				this.frm.add_custom_button(label, () => this.send_sms('Congratulations'),
					__("Notify"));
			}

			this.frm.add_custom_button(__("Custom Message"), () => this.send_sms('Custom Message'),
				__("Notify"));
		}
	}

	send_sms(notification_type) {
		new frappe.SMSManager(this.frm.doc, {
			notification_type: notification_type,
			mobile_no: this.frm.doc.contact_mobile,
			party_doctype: 'Customer',
			party: this.frm.doc.customer
		});
	}

	company() {
		this.set_customer_is_company_label();
		if (this.frm.doc.customer_is_company) {
			this.get_customer_details();
		}
	}

	customer() {
		this.get_customer_details();
	}

	customer_is_company() {
		if (this.frm.doc.customer_is_company) {
			this.frm.doc.customer = "";
			this.frm.refresh_field('customer');
			this.frm.set_value("customer_name", this.frm.doc.company);
		} else {
			this.frm.set_value("customer_name", "");
		}

		this.get_customer_details();
	}

	item_code() {
		var me = this;
		this.get_item_details(r => {
			me.frm.set_value("vehicle_allocation", null);
		});
	}

	vehicle_allocation_required() {
		if (!this.frm.doc.vehicle_allocation_required) {
			this.frm.set_value("vehicle_allocation", null);
			this.frm.set_value("allocation_period", null);
		}
	}

	vehicle_allocation() {
		var me = this;
		if (me.frm.doc.vehicle_allocation) {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_allocation.vehicle_allocation.get_allocation_details",
				args: {
					vehicle_allocation: this.frm.doc.vehicle_allocation,
				},
				callback: function (r) {
					if (r.message && !r.exc) {
						$.each(['delivery_period', 'allocation_period'], function (i, fn) {
							if (r.message[fn]) {
								me.frm.doc[fn] = r.message[fn];
								me.frm.refresh_field(fn);
								delete r.message[fn];
							}
						});

						me.frm.set_value(r.message);
					}
				}
			});
		} else {
			me.frm.set_value("allocation_title", "");
		}
	}

	allocation_period() {
		var me = this;

		if (me.frm.doc.allocation_period) {
			me.frm.set_value("vehicle_allocation", null);
		}
	}

	delivery_period() {
		super.delivery_period();

		if (this.frm.doc.delivery_period) {
			this.frm.set_value("vehicle_allocation", null);
			this.frm.set_value("allocation_period", null);
		}
	}

	vehicle() {
		this.warn_vehicle_reserved();
	}

	make_payment_entry(party_type) {
		if (['Customer', 'Supplier', 'Company'].includes(party_type)) {
			return frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_payment.vehicle_booking_payment.get_payment_entry",
				args: {
					"vehicle_booking_order": this.frm.doc.name,
					"party_type": party_type,
				},
				callback: function (r) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			});
		}
	}

	make_next_document(doctype) {
		if (!doctype)
			return;

		return frappe.call({
			method: "erpnext.vehicles.doctype.vehicle_booking_order.vehicle_booking_order.get_next_document",
			args: {
				"vehicle_booking_order": this.frm.doc.name,
				"doctype": doctype
			},
			callback: function (r) {
				if (!r.exc) {
					var doclist = frappe.model.sync(r.message);
					frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
				}
			}
		});
	}

	change_vehicle() {
		var me = this;

		var call_change_vehicle = function (vehicle) {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_order.change_booking.change_vehicle",
				args: {
					vehicle_booking_order: me.frm.doc.name,
					vehicle: vehicle
				},
				callback: function (r) {
					if (!r.exc) {
						me.frm.reload_doc();
						dialog.hide();
					}
				}
			});
		}

		var dialog = new frappe.ui.Dialog({
			title: __("Select Vehicle"),
			fields: [
				{
					label: __("Vehicle"), fieldname: "vehicle", fieldtype: "Link", options: "Vehicle", reqd: 1,
					onchange: () => {
						let vehicle = dialog.get_value('vehicle');
						if (vehicle) {
							frappe.db.get_value("Vehicle", vehicle, ['color', 'chassis_no', 'engine_no', 'warranty_no', 'dispatch_date'], (r) => {
								if (r) {
									dialog.set_values(r);
								}
							});

							me.warn_vehicle_reserved(vehicle);
						}
					}, get_query: () => me.vehicle_query(), get_route_options_for_new_doc: () => me.vehicle_route_options()
				},
				{label: __("Chassis No"), fieldname: "chassis_no", fieldtype: "Data", read_only: 1},
				{label: __("Engine No"), fieldname: "engine_no", fieldtype: "Data", read_only: 1},
				{label: __("Color"), fieldname: "color", fieldtype: "Link", options: "Vehicle Color", read_only: 1},
				{label: __("Warranty Number"), fieldname: "warranty_no", fieldtype: "Data", read_only: 1},
				{label: __("Dispatch Date"), fieldname: "dispatch_date", fieldtype: "Date", read_only: 1},
				{label: __("Remove Vehicle"), fieldname: "remove_vehicle", fieldtype: "Button",
					hidden: me.frm.doc.vehicle ? 0 : 1, click: () => call_change_vehicle('')}
			]
		});

		dialog.set_primary_action(__("Change"), function () {
			call_change_vehicle(dialog.get_value('vehicle'));
		});
		dialog.show();
	}

	change_allocation() {
		var me = this;

		var call_change_allocation = function (vehicle_allocation) {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_order.change_booking.change_allocation",
				args: {
					vehicle_booking_order: me.frm.doc.name,
					vehicle_allocation: vehicle_allocation
				},
				callback: function (r) {
					if (!r.exc) {
						me.frm.reload_doc();
						dialog.hide();
					}
				}
			});
		}

		var dialog = new frappe.ui.Dialog({
			title: __("Select Allocation"),
			fields: [
				{
					label: __("Vehicle Allocation"), fieldname: "vehicle_allocation", fieldtype: "Link", options: "Vehicle Allocation", reqd: 1,
					onchange: () => {
						let allocation = dialog.get_value('vehicle_allocation');
						if (allocation) {
							frappe.db.get_value("Vehicle Allocation", allocation, ['title', 'allocation_period', 'delivery_period'], (r) => {
								if (r) {
									dialog.set_values(r);
								}
							});
						}
					}, get_query: () => me.allocation_query(true, dialog), get_route_options_for_new_doc: () => me.allocation_route_options(dialog)
				},
				{label: __("Delivery Period"), fieldname: "delivery_period", fieldtype: "Link", options: "Vehicle Allocation Period",
					default: me.frm.doc.delivery_period, bold: 1, get_query: () => me.delivery_period_query(true)},
				{label: __("Allocation Code / Sr #"), fieldname: "title", fieldtype: "Data", read_only: 1},
				{label: __("Allocation Period"), fieldname: "allocation_period", fieldtype: "Link", options: "Vehicle Allocation Period", read_only: 1},
				{label: __("Remove Allocation"), fieldname: "remove_allocation", fieldtype: "Button",
					hidden: me.frm.doc.vehicle_allocation ? 0 : 1, click: () => call_change_allocation('')}
			]
		});

		dialog.set_primary_action(__("Change"), function () {
			call_change_allocation(dialog.get_value('vehicle_allocation'));
		});
		dialog.show();
	}

	change_delivery_period() {
		var me = this;
		var dialog = new frappe.ui.Dialog({
			title: __("Select Delivery Period"),
			fields: [
				{label: __("Delivery Period"), fieldname: "delivery_period", fieldtype: "Link", options: "Vehicle Allocation Period",
					reqd: 1, get_query: () => me.delivery_period_query(true)}
			]
		});

		dialog.set_primary_action(__("Change"), function () {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_order.change_booking.change_delivery_period",
				args: {
					vehicle_booking_order: me.frm.doc.name,
					delivery_period: dialog.get_value('delivery_period')
				},
				callback: function (r) {
					if (!r.exc) {
						me.frm.reload_doc();
						dialog.hide();
					}
				}
			});
		});
		dialog.show();
	}

	change_outstation_delivery() {
		var me = this;

		var new_outstation_delivery = cint(me.frm.doc.outstation_delivery) ? 0 : 1;
		var action_label = new_outstation_delivery ? "Enable Outstation Delivery" : "Disable Outstation Delivery";

		frappe.confirm(__(`Are you sure you want to <b>${__(action_label)}</b> for this booking order?`),
			function() {
				frappe.call({
					method: "erpnext.vehicles.doctype.vehicle_booking_order.change_booking.change_outstation_delivery",
					args: {
						vehicle_booking_order: me.frm.doc.name,
						outstation_delivery: new_outstation_delivery
					},
					callback: function (r) {
						if (!r.exc) {
							me.frm.reload_doc();
						}
					}
				});
			}
		);
	}

	change_color() {
		var me = this;
		var dialog = new frappe.ui.Dialog({
			title: __("Select Color"),
			fields: [
				{label: __("Color (1st Priority)"), fieldname: "color_1", fieldtype: "Link", options: "Vehicle Color", reqd: 1,
					get_query: () => me.color_query()},
				{label: __("Color (2nd Priority)"), fieldname: "color_2", fieldtype: "Link", options: "Vehicle Color",
					get_query: () => me.color_query()},
				{label: __("Color (3rd Priority)"), fieldname: "color_3", fieldtype: "Link", options: "Vehicle Color",
					get_query: () => me.color_query()},
			]
		});

		dialog.set_primary_action(__("Change"), function () {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_order.change_booking.change_color",
				args: {
					vehicle_booking_order: me.frm.doc.name,
					color_1: dialog.get_value('color_1'),
					color_2: dialog.get_value('color_2'),
					color_3: dialog.get_value('color_3'),
				},
				callback: function (r) {
					if (!r.exc) {
						me.frm.reload_doc();
						dialog.hide();
					}
				}
			});
		});
		dialog.show();
	}

	change_customer_details() {
		var me = this;

		var get_customer_details = function (keep_contact) {
			var values = dialog.get_values(true);
			if (values.customer || values.customer_is_company) {
				frappe.call({
					method: "erpnext.vehicles.vehicle_booking_controller.get_customer_details",
					args: {
						args: {
							company: me.frm.doc.company,
							item_code: me.frm.doc.item_code,
							transaction_date: me.frm.doc.transaction_date,
							delivery_date: me.frm.doc.delivery_date,
							customer: values.customer,
							customer_is_company: values.customer_is_company,
							financer: values.financer,
							finance_type: values.finance_type,
							customer_address: keep_contact ? values.customer_address : "",
							contact_person: keep_contact ? values.contact_person : "",
							financer_contact_person: keep_contact ? values.financer_contact_person : "",
						},
						get_withholding_tax: 0
					},
					callback: function (r) {
						if (r.message && !r.exc) {
							dialog.set_values(r.message);
						}
					}
				});
			}
		};

		var get_address_display = function () {
			var values = dialog.get_values(true);
			frappe.call({
				method: "erpnext.vehicles.vehicle_booking_controller.get_address_details",
				args: {
					address: cstr(values.customer_address),
				},
				callback: function (r) {
					if (r.message && !r.exc) {
						dialog.set_values(r.message);
					}
				}
			});
		};

		var get_contact_details = function () {
			var values = dialog.get_values(true);
			frappe.call({
				method: "erpnext.vehicles.vehicle_booking_controller.get_customer_contact_details",
				args: {
					args: {
						customer: values.customer,
						financer: values.financer,
						finance_type: values.finance_type
					},
					customer_contact: values.contact_person,
					financer_contact: values.financer_contact_person
				},
				callback: function (r) {
					if (r.message && !r.exc) {
						dialog.set_values(r.message);
					}
				}
			});
		};

		var dialog = new frappe.ui.Dialog({
			title: __("Update Customer Details"),
			size: 'large',
			fields: [
				{label: __("Customer is {0}", [me.frm.doc.company]), fieldname: "customer_is_company", fieldtype: "Check",
					default: me.frm.doc.customer_is_company, depends_on: "eval:!doc.customer",
					change: () => get_customer_details()
				},

				{label: __("Customer (User)"), fieldname: "customer", fieldtype: "Link", options: "Customer",
					default: me.frm.doc.customer, bold: 1,
					depends_on: "eval:!doc.customer_is_company",
					get_query: () => erpnext.queries.customer(),
					change: () => get_customer_details()
				},

				{label: __("Lessee/User Name"), fieldname: "lessee_name", fieldtype: "Data",
					default: me.frm.doc.lessee_name, read_only: 1},

				{label: __("Customer Name"), fieldname: "customer_name", fieldtype: "Data",
					default: me.frm.doc.customer_name, read_only: 1},

				{fieldtype: 'Column Break'},

				{label: __("Financer"), fieldname: "financer", fieldtype: "Link", options: "Customer",
					default: me.frm.doc.financer,
					get_query: () => erpnext.queries.customer(),
					change: () => get_customer_details()
				},

				{label: __("Financer Name"), fieldname: "financer_name", fieldtype: "Data",
					default: me.frm.doc.financer_name, read_only: 1},

				{label: __("Finance Type"), fieldname: "finance_type", fieldtype: "Select", options: "\nFinanced\nLeased",
					default: me.frm.doc.finance_type,
					depends_on: "financer",
					change: () => get_customer_details()
				},

				{fieldtype: 'Section Break'},

				{label: __("Address"), fieldname: "customer_address", fieldtype: "Link", options: "Address",
					default: me.frm.doc.customer_address,
					get_query: () => {
						var values = dialog.get_values(true);
						me.set_dynamic_link(values);
						return erpnext.queries.address_query(values);
					},
					change: () => get_address_display()
				},

				{fieldtype: 'Column Break'},

				{label: __("Address Display"), fieldname: "address_display", fieldtype: "Small Text",
					default: me.frm.doc.address_display, read_only: 1},

				{fieldtype: 'Section Break'},

				{label: __("Customer Contact Person"), fieldname: "contact_person", fieldtype: "Link", options: "Contact",
					default: me.frm.doc.contact_person,
					get_query: () => {
						var values = dialog.get_values(true);
						me.set_customer_dynamic_link(values);
						return erpnext.queries.contact_query(values);
					},
					change: () => get_contact_details()
				},

				{label: __("Customer Contact Name"), fieldname: "contact_display", fieldtype: "Data",
					default: me.frm.doc.contact_display, read_only: 1},

				{label: __("Financer Contact Person"), fieldname: "financer_contact_person", fieldtype: "Link", options: "Contact",
					default: me.frm.doc.financer_contact_person,
					depends_on: "financer",
					get_query: () => {
						var values = dialog.get_values(true);
						me.set_financer_dynamic_link(values);
						return erpnext.queries.contact_query(values);
					},
					change: () => get_contact_details()
				},

				{label: __("Financer Contact Name"), fieldname: "financer_contact_display", fieldtype: "Data",
					default: me.frm.doc.financer_contact_display, read_only: 1,
					depends_on: "financer"},

				{fieldtype: 'Column Break'},

				{label: __("Contact Email"), fieldname: "contact_email", fieldtype: "Data",
					default: me.frm.doc.contact_email, read_only: 1},

				{label: __("Contact Mobile"), fieldname: "contact_mobile", fieldtype: "Data",
					default: me.frm.doc.contact_mobile, read_only: 1},

				{label: __("Contact Phone"), fieldname: "contact_phone", fieldtype: "Data",
					default: me.frm.doc.contact_phone, read_only: 1},
			]
		});

		dialog.set_primary_action(__("Change/Update"), function () {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_order.change_booking.change_customer_details",
				args: {
					vehicle_booking_order: me.frm.doc.name,
					customer_is_company: dialog.get_value('customer_is_company'),
					customer: dialog.get_value('customer'),
					financer: dialog.get_value('financer'),
					finance_type: dialog.get_value('finance_type'),
					customer_address: dialog.get_value('customer_address'),
					contact_person: dialog.get_value('contact_person'),
					financer_contact_person: dialog.get_value('financer_contact_person'),
				},
				callback: function (r) {
					if (!r.exc) {
						me.frm.reload_doc();
						dialog.hide();
					}
				}
			});
		});

		get_customer_details(true);
		dialog.show();
	}

	change_item() {
		var me = this;

		frappe.db.get_value("Item", me.frm.doc.item_code, 'variant_of', (r) => {
			var variant_of = r.variant_of;
			var item_filters = {"is_vehicle": 1, "include_in_vehicle_booking": 1, "item_code": ['!=', me.frm.doc.item_code]}
			if (variant_of) {
				item_filters['variant_of'] = variant_of;
			}

			var dialog = new frappe.ui.Dialog({
				title: __("Change Vehicle Item (Variant)"),
				fields: [
					{
						label: __("Variant Item Code"), fieldname: "item_code", fieldtype: "Link", options: "Item", reqd: 1,
						onchange: () => {
							let item_code = dialog.get_value('item_code');
							if (item_code) {
								frappe.db.get_value("Item", item_code, 'item_name', (r) => {
									if (r) {
										dialog.set_values(r);
									}
								});
							}
						},
						get_query: () => erpnext.queries.item(item_filters)
					},
					{label: __("Variant Item Name"), fieldname: "item_name", fieldtype: "Data", read_only: 1}
				]
			});

			dialog.set_primary_action(__("Change"), function () {
				frappe.call({
					method: "erpnext.vehicles.doctype.vehicle_booking_order.change_booking.change_item",
					args: {
						vehicle_booking_order: me.frm.doc.name,
						item_code: dialog.get_value('item_code')
					},
					callback: function (r) {
						if (!r.exc) {
							me.frm.reload_doc();
							dialog.hide();
						}
					}
				});
			});
			dialog.show();
		});
	}

	change_payment_adjustment() {
		var me = this;
		var dialog = new frappe.ui.Dialog({
			title: __("Change Payment Adjustment"),
			fields: [
				{label: __("Payment Adjustment Amount"), fieldname: "payment_adjustment", fieldtype: "Currency",
					options: "Company:company:default_currency", reqd: 1,
					description: __(frappe.meta.get_docfield("Vehicle Booking Order", "payment_adjustment").description)},
			]
		});

		dialog.set_primary_action(__("Change"), function () {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_order.change_booking.change_payment_adjustment",
				args: {
					vehicle_booking_order: me.frm.doc.name,
					payment_adjustment: dialog.get_value('payment_adjustment')
				},
				callback: function (r) {
					if (!r.exc) {
						me.frm.reload_doc();
						dialog.hide();
					}
				}
			});
		});
		dialog.show();
	}

	change_vehicle_price() {
		var me = this;

		var update_invoice_total_in_dialog = function () {
			var invoice_total = flt(dialog.get_value('vehicle_amount')) + flt(dialog.get_value('fni_amount'))
				+ flt(dialog.get_value('withholding_tax_amount'));
			dialog.set_value('invoice_total', invoice_total);
		};

		var dialog = new frappe.ui.Dialog({
			title: __("Change Vehicle Price"),
			fields: [
				{label: __("New Vehicle Retail Price"), fieldname: "vehicle_amount", fieldtype: "Currency",
					options: "Company:company:default_currency", reqd: 1, onchange: () => update_invoice_total_in_dialog()},
				{label: __("New Freight and Insurance"), fieldname: "fni_amount", fieldtype: "Currency",
					options: "Company:company:default_currency", onchange: () => update_invoice_total_in_dialog()},
				{label: __("New Withholding Tax Amount"), fieldname: "withholding_tax_amount", fieldtype: "Currency",
					options: "Company:company:default_currency", read_only: 1, onchange: () => update_invoice_total_in_dialog()},
				{label: __("New Invoice Total"), fieldname: "invoice_total", fieldtype: "Currency",
					options: "Company:company:default_currency", read_only: 1},
			]
		});

		dialog.set_primary_action(__("Change"), function () {
			frappe.call({
				method: "erpnext.vehicles.doctype.vehicle_booking_order.change_booking.change_vehicle_price",
				args: {
					vehicle_booking_order: me.frm.doc.name,
					vehicle_amount: dialog.get_value('vehicle_amount'),
					fni_amount: dialog.get_value('fni_amount'),
				},
				callback: function (r) {
					if (!r.exc) {
						me.frm.reload_doc();
						dialog.hide();
					}
				}
			});
		});

		frappe.call({
			method: "get_party_tax_status",
			doc: me.frm.doc,
			callback: function (r1) {
				if (!r1.exc) {
					var tax_status = cstr(r1.message);

					frappe.call({
						method: "erpnext.vehicles.vehicle_booking_controller.get_vehicle_price",
						args: {
							company: me.frm.doc.company,
							item_code: me.frm.doc.item_code,
							vehicle_price_list: me.frm.doc.vehicle_price_list,
							fni_price_list: me.frm.doc.fni_price_list,
							tax_status: tax_status,
							transaction_date: me.frm.doc.transaction_date,
							delivery_date: me.frm.doc.delivery_date,
						},
						callback: function (r2) {
							if (!r2.exc) {
								dialog.set_values(r2.message);
								update_invoice_total_in_dialog();
								dialog.show();
							}
						}
					});
				}
			}
		});
	}

	change_priority() {
		var me = this;

		var new_priority = cint(me.frm.doc.priority) ? 0 : 1;
		var priority_label = new_priority ? "High" : "Normal";

		frappe.confirm(__(`Are you sure you want to change the priority to <b>${__(priority_label)}</b>?`),
			function() {
				frappe.call({
					method: "erpnext.vehicles.doctype.vehicle_booking_order.change_booking.change_priority",
					args: {
						vehicle_booking_order: me.frm.doc.name,
						priority: new_priority
					},
					callback: function (r) {
						if (!r.exc) {
							me.frm.reload_doc();
						}
					}
				});
			}
		)
	}

	change_cancellation() {
		var me = this;

		var cancelled = cint(me.frm.doc.status === "Cancelled Booking") ? 0 : 1;
		var cancellation_label = cancelled ? "Cancel Booking" : "Re-Open Booking";

		frappe.confirm(__(`Are you sure you want to <b>${__(cancellation_label)}</b>`),
			function() {
				frappe.call({
					method: "erpnext.vehicles.doctype.vehicle_booking_order.change_booking.change_cancellation",
					args: {
						vehicle_booking_order: me.frm.doc.name,
						cancelled: cancelled
					},
					callback: function (r) {
						if (!r.exc) {
							me.frm.reload_doc();
						}
					}
				});
			}
		)
	}

	change_pdi_requested() {
		var me = this;

		var new_pdi_requested = cint(me.frm.doc.pdi_requested) ? 0 : 1;
		var label = new_pdi_requested ? "request Pre-Delivery Inspection" : "cancel Pre-Delivery Inspection request";

		frappe.confirm(__(`Are you sure you want to ${__(label)}?`),
			function() {
				frappe.call({
					method: "erpnext.vehicles.doctype.vehicle_booking_order.change_booking.change_pdi_requested",
					args: {
						vehicle_booking_order: me.frm.doc.name,
						pdi_requested: new_pdi_requested
					},
					callback: function (r) {
						if (!r.exc) {
							me.frm.reload_doc();
						}
					}
				});
			}
		)
	}

	can_change(what) {
		if (this.frm.doc.__onload && this.frm.doc.__onload.can_change) {
			return this.frm.doc.__onload.can_change[what];
		} else {
			return false;
		}
	}

	can_notify(what) {
		if (this.frm.doc.__onload && this.frm.doc.__onload.can_notify) {
			return this.frm.doc.__onload.can_notify[what];
		} else {
			return false;
		}
	}
};

extend_cscript(cur_frm.cscript, new erpnext.vehicles.VehicleBookingOrder({frm: cur_frm}));
