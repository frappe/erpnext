frappe.provide("erpnext.vehicles");

erpnext.vehicles.VehicleTransactionController = class VehicleTransactionController extends erpnext.stock.StockController {
	setup() {
		if (this.frm.fields_dict.posting_time) {
			this.setup_posting_date_time_check();
		}
	}

	onload() {
		this.setup_queries();
	}

	refresh() {
		erpnext.toggle_naming_series();
		erpnext.hide_company();
		this.set_customer_dynamic_link();
		this.setup_route_options();
	}

	setup_queries() {
		var me = this;

		this.setup_warehouse_query();

		if (this.frm.fields_dict.customer) {
			this.frm.set_query('customer', erpnext.queries.customer);
		}
		if (this.frm.fields_dict.financer) {
			this.frm.set_query('financer', erpnext.queries.customer);
		}
		if (this.frm.fields_dict.vehicle_owner) {
			this.frm.set_query('vehicle_owner', erpnext.queries.customer);
		}
		if (this.frm.fields_dict.registration_customer) {
			this.frm.set_query('registration_customer', erpnext.queries.customer);
		}
		if (this.frm.fields_dict.broker) {
			this.frm.set_query('broker', erpnext.queries.customer);
		}

		if (this.frm.fields_dict.supplier) {
			this.frm.set_query('supplier', erpnext.queries.supplier);
		}

		if (this.frm.fields_dict.contact_person) {
			this.frm.set_query('contact_person', () => {
				me.set_customer_dynamic_link();
				return erpnext.queries.contact_query(me.frm.doc);
			});
		}

		if (this.frm.fields_dict.customer_address) {
			this.frm.set_query('customer_address', () => {
				me.set_customer_dynamic_link();
				return erpnext.queries.address_query(me.frm.doc);
			});
		}

		if (this.frm.fields_dict.receiver_contact) {
			this.frm.set_query('receiver_contact', () => {
				me.set_receiver_dynamic_link();
			});
		}

		erpnext.queries.setup_queries(this.frm, "Item", function() {
			var filters = {"is_vehicle": 1};
			if (me.frm.doc.vehicle_booking_order
					|| ['Vehicle Invoice', 'Vehicle Invoice Delivery'].includes(me.frm.doc.doctype)) {
				filters.include_in_vehicle_booking = 1;
			}
			return erpnext.queries.item(filters);
		});

		if (this.frm.fields_dict.transporter) {
			this.frm.set_query('transporter', function () {
				return {
					filters: {
						'is_transporter': 1
					}
				}
			});
		}

		if (this.frm.fields_dict.driver) {
			this.frm.set_query('driver', function () {
				return {
					filters: {
						'transporter': me.frm.doc.transporter
					}
				}
			});
		}
	}

	setup_route_options() {
		var vehicle_field = this.frm.get_docfield("vehicle");
		var transporter_field = this.frm.get_docfield("transporter");
		var driver_field = this.frm.get_docfield("driver");

		if (vehicle_field) {
			vehicle_field.get_route_options_for_new_doc = () => {
				return {
					"item_code": this.frm.doc.item_code,
					"item_name": this.frm.doc.item_name
				}
			};
		}

		if (transporter_field) {
			transporter_field.get_route_options_for_new_doc = () => {
				return {
					"is_transporter": 1
				}
			};
		}

		if (driver_field) {
			driver_field.get_route_options_for_new_doc = () => {
				return {
					"transporter": this.frm.doc.transporter
				}
			};
		}
	}

	set_customer_dynamic_link() {
		frappe.dynamic_link = {
			doc: this.frm.doc,
			fieldname: 'customer',
			doctype: 'Customer'
		};
	}

	set_receiver_dynamic_link() {
		var doctype = 'Customer';
		var fieldname = 'customer';

		if (this.frm.doc.transporter) {
			doctype = 'Supplier';
			fieldname = 'transporter';
		} else if (this.frm.doc.broker) {
			doctype = 'Customer';
			fieldname = 'broker';
		}

		frappe.dynamic_link = {
			doc: this.frm.doc,
			fieldname: fieldname,
			doctype: doctype
		};
	}

	customer() {
		this.get_customer_details();
	}

	financer() {
		this.get_customer_details();
	}

	vehicle_owner() {
		this.get_customer_details();
	}

	registration_customer() {
		this.get_customer_details();
	}

	vehicle(doc, cdt, cdn) {
		doc = this.frm.doc;
		if (cdt && cdn) {
			doc = frappe.get_doc(cdt, cdn);
		}
		this.get_vehicle_details(doc);
	}

	vehicle_booking_order(doc, cdt, cdn) {
		doc = this.frm.doc;
		if (cdt && cdn) {
			doc = frappe.get_doc(cdt, cdn);
		}
		this.get_vehicle_booking_order_details(doc);
	}

	project(doc, cdt, cdn) {
		doc = this.frm.doc;
		if (cdt && cdn) {
			doc = frappe.get_doc(cdt, cdn);
		}
		this.get_project_details(doc);
	}

	get_customer_details() {
		var me = this;

		return frappe.call({
			method: "erpnext.vehicles.vehicle_transaction_controller.get_customer_details",
			args: {
				args: {
					doctype: me.frm.doc.doctype,
					company: me.frm.doc.company,
					customer: me.frm.doc.customer,
					financer: me.frm.doc.financer,
					vehicle_owner: me.frm.doc.vehicle_owner,
					registration_customer: me.frm.doc.registration_customer,
					supplier: me.frm.doc.supplier,
					vehicle_booking_order: me.frm.doc.vehicle_booking_order,
					posting_date: me.frm.doc.posting_date || me.frm.doc.transaction_date
				}
			},
			callback: function (r) {
				if (r.message && !r.exc) {
					me.frm.set_value(r.message);
				}
			}
		});
	}

	get_vehicle_booking_order_details(doc) {
		var me = this;
		if (!doc) {
			doc = me.frm.doc;
		}

		return frappe.call({
			method: "erpnext.vehicles.vehicle_transaction_controller.get_vehicle_booking_order_details",
			args: {
				args: {
					doctype: me.frm.doc.doctype,
					company: me.frm.doc.company,
					customer: me.frm.doc.customer,
					supplier: me.frm.doc.supplier,
					vehicle_booking_order: doc.vehicle_booking_order,
					project: doc.project,
					vehicle: doc.vehicle,
					posting_date: me.frm.doc.posting_date || me.frm.doc.transaction_date,
					issued_for: me.frm.doc.issued_for,
				}
			},
			callback: function (r) {
				if (r.message && !r.exc) {
					if (doc == me.frm.doc) {
						me.frm.set_value(r.message);
					} else {
						frappe.model.set_value(doc.doctype, doc.name, r.message);
					}
				}
			}
		});
	}

	get_project_details(doc) {
		var me = this;
		if (!doc) {
			doc = me.frm.doc;
		}

		return frappe.call({
			method: "erpnext.vehicles.vehicle_transaction_controller.get_project_details",
			args: {
				args: {
					doctype: me.frm.doc.doctype,
					company: me.frm.doc.company,
					customer: me.frm.doc.customer,
					supplier: me.frm.doc.supplier,
					project: doc.project,
					vehicle_booking_order: doc.vehicle_booking_order,
					vehicle: doc.vehicle,
					posting_date: me.frm.doc.posting_date || me.frm.doc.transaction_date,
					issued_for: me.frm.doc.issued_for,
				}
			},
			callback: function (r) {
				if (r.message && !r.exc) {
					if (doc == me.frm.doc) {
						me.frm.set_value(r.message).then(() => {
							if (r.message.vehicle_checklist) {
								me.frm.trigger('vehicle_checklist');
							}
						});
					} else {
						frappe.model.set_value(doc.doctype, doc.name, r.message);
					}
				}
			}
		});
	}

	get_vehicle_details(doc) {
		var me = this;
		if (!doc) {
			doc = me.frm.doc;
		}

		return frappe.call({
			method: "erpnext.vehicles.vehicle_transaction_controller.get_vehicle_details",
			args: {
				args: {
					doctype: me.frm.doc.doctype,
					vehicle: doc.vehicle,
					customer: me.frm.doc.customer,
					is_return: me.frm.doc.is_return,
					posting_date: me.frm.doc.posting_date || me.frm.doc.transaction_date,
					item_code: me.frm.doc.item_code,
					issued_for: me.frm.doc.issued_for,
				}
			},
			callback: function (r) {
				if (r.message && !r.exc) {
					if (doc == me.frm.doc) {
						me.frm.set_value(r.message);
					} else {
						frappe.model.set_value(doc.doctype, doc.name, r.message);
					}
				}
			}
		});
	}

	customer_address() {
		if (this.frm.fields_dict.address_display) {
			erpnext.utils.get_address_display(this.frm, "customer_address", "address_display");
		}
	}

	contact_person() {
		this.get_contact_details(this.frm.doc.contact_person, "");
	}

	receiver_contact() {
		this.get_contact_details(this.frm.doc.receiver_contact, "receiver_");
	}

	get_contact_details(contact, prefix) {
		var me = this;
		return frappe.call({
			method: "erpnext.vehicles.vehicle_transaction_controller.get_contact_details",
			args: {
				contact: contact,
				prefix: prefix
			},
			callback: function (r) {
				if (r.message && !r.exc) {
					me.frm.set_value(r.message);
				}
			}
		});
	}
};

