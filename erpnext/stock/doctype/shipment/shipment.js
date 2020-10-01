// Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shipment', {
	address_query: function(frm, link_doctype, link_name, is_your_company_address) {
		return {
			query: 'frappe.contacts.doctype.address.address.address_query',
			filters: {
				link_doctype: link_doctype,
				link_name: link_name,
				is_your_company_address: is_your_company_address
			}
		};
	},
	contact_query: function(frm, link_doctype, link_name) {
		return {
			query: 'frappe.contacts.doctype.contact.contact.contact_query',
			filters: {
				link_doctype: link_doctype,
				link_name: link_name
			}
		};
	},
	onload: function(frm) {
		frm.set_query("delivery_address_name", () => {
			let link_doctype = '';
			let link_name = '';
			let is_your_company_address = 0;
			if (frm.doc.delivery_to_type == 'Customer') {
				link_doctype = 'Customer';
				link_name = frm.doc.delivery_customer;
			}
			if (frm.doc.delivery_to_type == 'Supplier') {
				link_doctype = 'Supplier';
				link_name = frm.doc.delivery_supplier;
			}
			if (frm.doc.delivery_to_type == 'Company') {
				link_doctype = 'Company';
				link_name = frm.doc.delivery_company;
				is_your_company_address = 1;
			}
			return frm.events.address_query(frm, link_doctype, link_name, is_your_company_address);
		});
		frm.set_query("pickup_address_name", () => {
			let link_doctype = '';
			let link_name = '';
			let is_your_company_address = 0;
			if (frm.doc.pickup_from_type == 'Customer') {
				link_doctype = 'Customer';
				link_name = frm.doc.pickup_customer;
			}
			if (frm.doc.pickup_from_type == 'Supplier') {
				link_doctype = 'Supplier';
				link_name = frm.doc.pickup_supplier;
			}
			if (frm.doc.pickup_from_type == 'Company') {
				link_doctype = 'Company';
				link_name = frm.doc.pickup_company;
				is_your_company_address = 1;
			}
			return frm.events.address_query(frm, link_doctype, link_name, is_your_company_address);
		});
		frm.set_query("delivery_contact_name", () => {
			let link_doctype = '';
			let link_name = '';
			if (frm.doc.delivery_to_type == 'Customer') {
				link_doctype = 'Customer';
				link_name = frm.doc.delivery_customer;
			}
			if (frm.doc.delivery_to_type == 'Supplier') {
				link_doctype = 'Supplier';
				link_name = frm.doc.delivery_supplier;
			}
			if (frm.doc.delivery_to_type == 'Company') {
				link_doctype = 'Company';
				link_name = frm.doc.delivery_company;
			}
			return frm.events.contact_query(frm, link_doctype, link_name);
		});
		frm.set_query("pickup_contact_name", () => {
			let link_doctype = '';
			let link_name = '';
			if (frm.doc.pickup_from_type == 'Customer') {
				link_doctype = 'Customer';
				link_name = frm.doc.pickup_customer;
			}
			if (frm.doc.pickup_from_type == 'Supplier') {
				link_doctype = 'Supplier';
				link_name = frm.doc.pickup_supplier;
			}
			if (frm.doc.pickup_from_type == 'Company') {
				link_doctype = 'Company';
				link_name = frm.doc.pickup_company;
			}
			return frm.events.contact_query(frm, link_doctype, link_name);
		});
		frm.set_query("delivery_note", "shipment_delivery_note", function() {
			let customer = '';
			if (frm.doc.delivery_to_type == "Customer") {
				customer = frm.doc.delivery_customer;
			}
			if (frm.doc.delivery_to_type == "Company") {
				customer = frm.doc.delivery_company;
			}
			if (customer) {
				return {
					filters: {
						customer: customer,
						docstatus: 1,
						status: ["not in", ["Cancelled"]]
					}
				};
			}
		});
	},
	refresh: function(frm) {
		if (frm.doc.docstatus === 1 && !frm.doc.shipment_id) {
			frm.add_custom_button(__('Fetch Shipping Rates'), function() {
				return frm.events.fetch_shipping_rates(frm);
			});
		}
		if (frm.doc.shipment_id) {
			frm.add_custom_button(__('Print Shipping Label'), function() {
				return frm.events.print_shipping_label(frm);
			}, __('Tools'));
			if (frm.doc.tracking_status != 'Delivered') {
				frm.add_custom_button(__('Update Tracking'), function() {
					return frm.events.update_tracking(frm, frm.doc.service_provider, frm.doc.shipment_id);
				}, __('Tools'));

				frm.add_custom_button(__('Track Status'), function() {
					const urls = frm.doc.tracking_url.split(', ');
					urls.forEach(url => window.open(url));
				}, __('View'));
			}
		}
		$('div[data-fieldname=pickup_address] > div > .clearfix').hide();
		$('div[data-fieldname=pickup_contact] > div > .clearfix').hide();
		$('div[data-fieldname=delivery_address] > div > .clearfix').hide();
		$('div[data-fieldname=delivery_contact] > div > .clearfix').hide();
	},
	before_save: function(frm) {
		if (frm.doc.delivery_to_type == 'Company') {
			frm.set_value("delivery_to", frm.doc.delivery_company);
		}
		if (frm.doc.delivery_to_type == 'Customer') {
			frm.set_value("delivery_to", frm.doc.delivery_customer);
		}
		if (frm.doc.delivery_to_type == 'Supplier') {
			frm.set_value("delivery_to", frm.doc.delivery_supplier);
		}
		if (frm.doc.pickup_from_type == 'Company') {
			frm.set_value("pickup", frm.doc.pickup_company);
		}
		if (frm.doc.pickup_from_type == 'Customer') {
			frm.set_value("pickup", frm.doc.pickup_customer);
		}
		if (frm.doc.pickup_from_type == 'Supplier') {
			frm.set_value("pickup", frm.doc.pickup_supplier);
		}
	},
	set_pickup_company_address: function(frm) {
		frappe.db.get_value('Address', {
			address_title: frm.doc.pickup_company,
			is_your_company_address: 1
		}, 'name', (r) => {
			frm.set_value("pickup_address_name", r.name);
		});
	},
	set_delivery_company_address: function(frm) {
		frappe.db.get_value('Address', {
			address_title: frm.doc.delivery_company,
			is_your_company_address: 1
		}, 'name', (r) => {
			frm.set_value("delivery_address_name", r.name);
		});
	},
	pickup_from_type: function(frm) {
		if (frm.doc.pickup_from_type == 'Company') {
			frm.set_value("pickup_company", frappe.defaults.get_default('company'));
			frm.set_value("pickup_customer", '');
			frm.set_value("pickup_supplier", '');
		}
		else {
			frm.trigger('clear_pickup_fields');
		}
		if (frm.doc.pickup_from_type == 'Customer') {
			frm.set_value("pickup_company", '');
			frm.set_value("pickup_supplier", '');
		}
		if (frm.doc.pickup_from_type == 'Supplier') {
			frm.set_value("pickup_customer", '');
			frm.set_value("pickup_company", '');
		}
		frm.events.remove_notific_child_table(frm, 'shipment_notification_subscription', 'Pickup');
		frm.events.remove_notific_child_table(frm, 'shipment_status_update_subscription', 'Pickup');
	},
	delivery_to_type: function(frm) {
		if (frm.doc.delivery_to_type == 'Company') {
			frm.set_value("delivery_company", frappe.defaults.get_default('company'));
			frm.set_value("delivery_customer", '');
			frm.set_value("delivery_supplier", '');
		}
		else {
			frm.trigger('clear_delivery_fields');
		}
		if (frm.doc.delivery_to_type == 'Customer') {
			frm.set_value("delivery_company", '');
			frm.set_value("delivery_supplier", '');
		}
		if (frm.doc.delivery_to_type == 'Supplier') {
			frm.set_value("delivery_customer", '');
			frm.set_value("delivery_company", '');
			frm.toggle_display("shipment_delivery_note", false);
		}
		else {
			frm.toggle_display("shipment_delivery_note", true);
		}
		frm.events.remove_notific_child_table(frm, 'shipment_notification_subscription', 'Delivery');
		frm.events.remove_notific_child_table(frm, 'shipment_status_update_subscription', 'Delivery');
	},
	delivery_address_name: function(frm) {
		if (frm.doc.delivery_to_type == 'Company') {
			erpnext.utils.get_address_display(frm, 'delivery_address_name', 'delivery_address', true);
		}
		else {
			erpnext.utils.get_address_display(frm, 'delivery_address_name', 'delivery_address', false);
		}
	},
	pickup_address_name: function(frm) {
		if (frm.doc.pickup_from_type == 'Company') {
			erpnext.utils.get_address_display(frm, 'pickup_address_name', 'pickup_address', true);
		}
		else {
			erpnext.utils.get_address_display(frm, 'pickup_address_name', 'pickup_address', false);
		}
	},
	get_contact_display: function(frm, contact_name, contact_type) {
		frappe.call({
			method: "frappe.contacts.doctype.contact.contact.get_contact_details",
			args: { contact: contact_name },
			callback: function(r) {
				if(r.message) {
					if (!(r.message.contact_email && (r.message.contact_phone || r.message.contact_mobile))) {
						if (contact_type == 'Delivery') {
							frm.set_value('delivery_contact_name', '');
							frm.set_value('delivery_contact', '');
						}
						else {
							frm.set_value('pickup_contact_name', '');
							frm.set_value('pickup_contact', '');
						}
						frappe.throw(__(`Email or Phone/Mobile of the Contact are mandatory to continue. </br>
							Please set Email/Phone for the contact <a href="#Form/Contact/${contact_name}">${contact_name}</a>`));
					}
					let contact_display = r.message.contact_display;
					if (r.message.contact_email) {
						contact_display += '<br>' + r.message.contact_email;
					}
					if (r.message.contact_phone) {
						contact_display += '<br>' + r.message.contact_phone;
					}
					if (r.message.contact_mobile && !r.message.contact_phone) {
						contact_display += '<br>' + r.message.contact_mobile;
					}
					if (contact_type == 'Delivery'){
						frm.set_value('delivery_contact', contact_display);
						if (r.message.contact_email) {
							frm.set_value('delivery_contact_email', r.message.contact_email);
						}
					}
					else {
						frm.set_value('pickup_contact', contact_display);
						if (r.message.contact_email) {
							frm.set_value('pickup_contact_email', r.message.contact_email);
						}
					}
				}
			}
		});
	},
	delivery_contact_name: function(frm) {
		if (frm.doc.delivery_contact_name) {
			frm.events.get_contact_display(frm, frm.doc.delivery_contact_name, 'Delivery');
		}
	},
	pickup_contact_name: function(frm) {
		if (frm.doc.pickup_contact_name) {
			frm.events.get_contact_display(frm, frm.doc.pickup_contact_name, 'Pickup');
		}
	},
	pickup_contact_person: function(frm) {
		if (frm.doc.pickup_contact_person) {
			frappe.call({
				method: "erpnext.stock.doctype.shipment.shipment.get_company_contact",
				args: { user: frm.doc.pickup_contact_person },
				callback: function({ message }) {
					const r = message;
					let contact_display = `${r.first_name} ${r.last_name}`;
					if (r.email) {
						contact_display += `<br>${ r.email }`;
						frm.set_value('pickup_contact_email', r.email);
					}
					if (r.phone) {
						contact_display += `<br>${ r.phone }`;
					}
					if (r.mobile_no && !r.phone) {
						contact_display += `<br>${ r.mobile_no }`;
					}
					frm.set_value('pickup_contact', contact_display);
				}
			});
		} else {
			if (frm.doc.pickup_from_type === 'Company') {
				frappe.call({
					method: "erpnext.stock.doctype.shipment.shipment.get_company_contact",
					args: { user: frappe.session.user },
					callback: function({ message }) {
						const r = message;
						let contact_display = `${r.first_name} ${r.last_name}`;
						if (r.email) {
							contact_display += `<br>${ r.email }`;
							frm.set_value('pickup_contact_email', r.email);
						}
						if (r.phone) {
							contact_display += `<br>${ r.phone }`;
						}
						if (r.mobile_no && !r.phone) {
							contact_display += `<br>${ r.mobile_no }`;
						}
						frm.set_value('pickup_contact', contact_display);
					}
				});
			}
		}
	},
	set_company_contact: function(frm, delivery_type) {
		frappe.db.get_value('User', { name: frappe.session.user }, ['full_name', 'last_name', 'email', 'phone', 'mobile_no'], (r) => {
			if (!(r.last_name && r.email && (r.phone || r.mobile_no))) {
				if (delivery_type == 'Delivery') {
					frm.set_value('delivery_company', '');
					frm.set_value('delivery_contact', '');
				}
				else {
					frm.set_value('pickup_company', '');
					frm.set_value('pickup_contact', '');
				}
				frappe.throw(__(`Last Name, Email or Phone/Mobile of the user are mandatory to continue. </br>
					Please first set Last Name, Email and Phone for the user <a href="#Form/User/${frappe.session.user}">${frappe.session.user}</a>`));
			}
			let contact_display = r.full_name;
			if (r.email) {
				contact_display += '<br>' + r.email;
			}
			if (r.phone) {
				contact_display += '<br>' + r.phone;
			}
			if (r.mobile_no && !r.phone) {
				contact_display += '<br>' + r.mobile_no;
			}
			if (delivery_type == 'Delivery') {
				frm.set_value('delivery_contact', contact_display);
				if (r.email) {
					frm.set_value('delivery_contact_email', r.email);
				}
			}
			else {
				frm.set_value('pickup_contact', contact_display);
				if (r.email) {
					frm.set_value('pickup_contact_email', r.email);
				}
			}
		});
		frm.set_value('pickup_contact_person', frappe.session.user);
	},
	pickup_company: function(frm) {
		if (frm.doc.pickup_from_type == 'Company'  && frm.doc.pickup_company) {
			frm.trigger('set_pickup_company_address');
			frm.events.set_company_contact(frm, 'Pickup');
		}
	},
	delivery_company: function(frm) {
		if (frm.doc.delivery_to_type == 'Company' && frm.doc.delivery_company) {
			frm.trigger('set_delivery_company_address');
			frm.events.set_company_contact(frm, 'Delivery');
		}
	},
	delivery_customer: function(frm) {
		frm.trigger('clear_delivery_fields');
		if (frm.doc.delivery_customer) {
			frm.events.set_address_name(frm,'Customer',frm.doc.delivery_customer, 'Delivery');
			frm.events.set_contact_name(frm,'Customer',frm.doc.delivery_customer, 'Delivery');
		}
	},
	delivery_supplier: function(frm) {
		frm.trigger('clear_delivery_fields');
		if (frm.doc.delivery_supplier) {
			frm.events.set_address_name(frm,'Supplier',frm.doc.delivery_supplier, 'Delivery');
			frm.events.set_contact_name(frm,'Supplier',frm.doc.delivery_supplier, 'Delivery');
		}
	},
	pickup_customer: function(frm) {
		if (frm.doc.pickup_customer) {
			frm.events.set_address_name(frm,'Customer',frm.doc.pickup_customer, 'Pickup');
			frm.events.set_contact_name(frm,'Customer',frm.doc.pickup_customer, 'Pickup');
		}
	},
	pickup_supplier: function(frm) {
		if (frm.doc.pickup_supplier) {
			frm.events.set_address_name(frm,'Supplier',frm.doc.pickup_supplier, 'Pickup');
			frm.events.set_contact_name(frm,'Supplier',frm.doc.pickup_supplier, 'Pickup');
		}
	},
	set_address_name: function(frm, ref_doctype, ref_docname, delivery_type) {
		frappe.call({
			method: "erpnext.stock.doctype.shipment.shipment.get_address_name",
			args: {
				ref_doctype: ref_doctype,
				docname: ref_docname
			},
			callback: function(r) {
				if(r.message) {
					if (delivery_type == 'Delivery') {
						frm.set_value('delivery_address_name', r.message);
					}
					else {
						frm.set_value('pickup_address_name', r.message);
					}
				}
			}
		});
	},
	set_contact_name: function(frm, ref_doctype, ref_docname, delivery_type) {
		frappe.call({
			method: "erpnext.stock.doctype.shipment.shipment.get_contact_name",
			args: {
				ref_doctype: ref_doctype,
				docname: ref_docname
			},
			callback: function(r) {
				if(r.message) {
					if (delivery_type == 'Delivery') {
						frm.set_value('delivery_contact_name', r.message);
					}
					else {
						frm.set_value('pickup_contact_name', r.message);
					}
				}
			}
		});
	},
	add_template: function(frm) {
		if (frm.doc.parcel_template) {
			frappe.model.with_doc("Shipment Parcel Template", frm.doc.parcel_template, () => {
				let parcel_template = frappe.model.get_doc("Shipment Parcel Template", frm.doc.parcel_template);
				let row = frappe.model.add_child(frm.doc, "Shipment Parcel", "shipment_parcel");
				row.length = parcel_template.length;
				row.width = parcel_template.width;
				row.height = parcel_template.height;
				row.weight = parcel_template.weight;
				frm.refresh_fields("shipment_parcel");
			});
		}
	},
	pickup_date: function(frm) {
		if (frm.doc.pickup_date < frappe.datetime.get_today()) {
			frappe.throw(__("Pickup Date cannot be before this day"));
		}
		if (frm.doc.pickup_date == frappe.datetime.get_today()) {
			var pickup_time = frm.events.get_pickup_time(frm);
			frm.set_value("pickup_from", pickup_time);
			frm.trigger('set_pickup_to_time');
		}
	},
	pickup_from: function(frm) {
		var pickup_time = frm.events.get_pickup_time(frm);
		if (frm.doc.pickup_from && frm.doc.pickup_date == frappe.datetime.get_today()) {
			let current_hour = pickup_time.split(':')[0];
			let current_min = pickup_time.split(':')[1];
			let pickup_hour = frm.doc.pickup_from.split(':')[0];
			let pickup_min = frm.doc.pickup_from.split(':')[1];
			if (pickup_hour < current_hour || (pickup_hour == current_hour && pickup_min < current_min)) {
				frm.set_value("pickup_from", pickup_time);
				frappe.throw(__("Pickup Time cannot be in the past"));
			}
		}
		frm.trigger('set_pickup_to_time');
	},
	get_pickup_time: function() {
		let current_hour = new Date().getHours();
		let current_min = new Date().toLocaleString('en-US', {minute: 'numeric'});
		if (current_min < 30) {
			current_min = '30';
		}
		else {
			current_min = '00';
			current_hour = Number(current_hour)+1;
		}
		if (Number(current_hour) > 19 || Number(current_hour) === 19){
			frappe.throw(__("Today's pickup time is over, please select different date"));
		}
		current_hour = (current_hour < 10) ? '0' + current_hour : current_hour;
		let pickup_time = current_hour +':'+ current_min;
		return pickup_time;
	},
	set_pickup_to_time: function(frm) {
		let pickup_to_hour = Number(frm.doc.pickup_from.split(':')[0])+5;
		if (Number(pickup_to_hour) > 19 || Number(pickup_to_hour) === 19){
			pickup_to_hour = 19;
		}
		let pickup_to_min = frm.doc.pickup_from.split(':')[1];
		let pickup_to = pickup_to_hour +':'+ pickup_to_min;
		frm.set_value("pickup_to", pickup_to);
	},
	clear_pickup_fields: function(frm) {
		let fields = ["pickup_address_name", "pickup_contact_name", "pickup_address", "pickup_contact", "pickup_contact_email", "pickup_contact_person"];
		for (let field of fields){
			frm.set_value(field,  '');
		}
	},
	clear_delivery_fields: function(frm) {
		let fields = ["delivery_address_name", "delivery_contact_name", "delivery_address", "delivery_contact", "delivery_contact_email"];
		for (let field of fields){
			frm.set_value(field,  '');
		}
	},
	pickup_from_send_shipping_notification: function(frm, cdt, cdn) {
		if (frm.doc.pickup_contact_email && frm.doc.pickup_from_send_shipping_notification
				&& !validate_duplicate(frm, 'shipment_notification_subscription', frm.doc.pickup_contact_email, locals[cdt][cdn].idx)) {
			let row = frappe.model.add_child(frm.doc, "Shipment Notification Subscription", "shipment_notification_subscription");
			row.email = frm.doc.pickup_contact_email;
			frm.refresh_fields("shipment_notification_subscription");
		}
		if (!frm.doc.pickup_from_send_shipping_notification) {
			frm.events.remove_email_row(frm, 'shipment_notification_subscription', frm.doc.pickup_contact_email);
			frm.refresh_fields("shipment_notification_subscription");
		}
	},
	pickup_from_subscribe_to_status_updates: function(frm, cdt, cdn) {
		if (frm.doc.pickup_contact_email && frm.doc.pickup_from_subscribe_to_status_updates
				&& !validate_duplicate(frm, 'shipment_status_update_subscription', frm.doc.pickup_contact_email, locals[cdt][cdn].idx)) {
			let row = frappe.model.add_child(frm.doc, "Shipment Status Update Subscription", "shipment_status_update_subscription");
			row.email = frm.doc.pickup_contact_email;
			frm.refresh_fields("shipment_status_update_subscription");
		}
		if (!frm.doc.pickup_from_subscribe_to_status_updates) {
			frm.events.remove_email_row(frm, 'shipment_status_update_subscription', frm.doc.pickup_contact_email);
			frm.refresh_fields("shipment_status_update_subscription");
		}
	},
	delivery_to_send_shipping_notification: function(frm, cdt, cdn) {
		if (frm.doc.delivery_contact_email && frm.doc.delivery_to_send_shipping_notification
				&& !validate_duplicate(frm, 'shipment_notification_subscription', frm.doc.delivery_contact_email, locals[cdt][cdn].idx)){
			let row = frappe.model.add_child(frm.doc, "Shipment Notification Subscription", "shipment_notification_subscription");
			row.email = frm.doc.delivery_contact_email;
			frm.refresh_fields("shipment_notification_subscription");
		}
		if (!frm.doc.delivery_to_send_shipping_notification) {
			frm.events.remove_email_row(frm, 'shipment_notification_subscription', frm.doc.delivery_contact_email);
			frm.refresh_fields("shipment_notification_subscription");
		}
	},
	delivery_to_subscribe_to_status_updates: function(frm, cdt, cdn) {
		if (frm.doc.delivery_contact_email && frm.doc.delivery_to_subscribe_to_status_updates
				&& !validate_duplicate(frm, 'shipment_status_update_subscription', frm.doc.delivery_contact_email, locals[cdt][cdn].idx)) {
			let row = frappe.model.add_child(frm.doc, "Shipment Status Update Subscription", "shipment_status_update_subscription");
			row.email = frm.doc.delivery_contact_email;
			frm.refresh_fields("shipment_status_update_subscription");
		}
		if (!frm.doc.delivery_to_subscribe_to_status_updates) {
			frm.events.remove_email_row(frm, 'shipment_status_update_subscription', frm.doc.delivery_contact_email);
			frm.refresh_fields("shipment_status_update_subscription");
		}
	},
	remove_email_row: function(frm, table, fieldname) {
		$.each(frm.doc[table] || [], function(i, detail) {
			if(detail.email === fieldname){
				cur_frm.get_field(table).grid.grid_rows[i].remove();
			}
		});
	},
	remove_notific_child_table: function(frm, table, delivery_type) {
		$.each(frm.doc[table] || [], function(i, detail) {
			if (detail.email != frm.doc.pickup_email ||  detail.email != frm.doc.delivery_email){
				cur_frm.get_field(table).grid.grid_rows[i].remove();
			}
		});
		frm.refresh_fields(table);
		if (delivery_type == 'Delivery') {
			frm.set_value("delivery_to_send_shipping_notification", 0);
			frm.set_value("delivery_to_subscribe_to_status_updates", 0);
			frm.refresh_fields("delivery_to_send_shipping_notification");
			frm.refresh_fields("delivery_to_subscribe_to_status_updates");
		}
		else {
			frm.set_value("pickup_from_send_shipping_notification", 0);
			frm.set_value("pickup_from_subscribe_to_status_updates", 0);
			frm.refresh_fields("pickup_from_send_shipping_notification");
			frm.refresh_fields("pickup_from_subscribe_to_status_updates");
		}
	},
	fetch_shipping_rates: function(frm) {
		if (!frm.doc.shipment_id) {
			frappe.call({
				method: "erpnext.stock.doctype.shipment.shipment.fetch_shipping_rates",
				freeze: true,
				freeze_message: __("Fetching Shipping Rates"),
				args: {
					pickup_from_type: frm.doc.pickup_from_type,
					delivery_to_type: frm.doc.delivery_to_type,
					pickup_address_name: frm.doc.pickup_address_name,
					delivery_address_name: frm.doc.delivery_address_name,
					shipment_parcel: frm.doc.shipment_parcel,
					description_of_content: frm.doc.description_of_content,
					pickup_date: frm.doc.pickup_date,
					pickup_contact_name: frm.doc.pickup_from_type === 'Company' ? frm.doc.pickup_contact_person : frm.doc.pickup_contact_name,
					delivery_contact_name: frm.doc.delivery_contact_name,
					value_of_goods: frm.doc.value_of_goods
				},
				callback: function(r) {
					if (r.message) {
						select_from_available_services(frm, r.message);
					}
					else {
						frappe.throw(__("No Shipment Services available"));
					}
				}
			});
		}
		else {
			frappe.throw(__("Shipment already created"));
		}
	},
	print_shipping_label: function(frm) {
		frappe.call({
			method: "erpnext.stock.doctype.shipment.shipment.print_shipping_label",
			freeze: true,
			freeze_message: __("Printing Shipping Label"),
			args: {
				shipment_id: frm.doc.shipment_id,
				service_provider: frm.doc.service_provider
			},
			callback: function(r) {
				if (r.message) {
					if (frm.doc.service_provider == "LetMeShip") {
						var array = JSON.parse(r.message);
						// Uint8Array for unsigned bytes
						array = new Uint8Array(array);
						const file = new Blob([array], {type: "application/pdf"});
						const file_url = URL.createObjectURL(file);
						window.open(file_url);
					}
					else {
						if (Array.isArray(r.message)) {
							r.message.forEach(url => window.open(url));
						} else {
							window.open(r.message);
						}
					}
				}
			}
		});
	},
	update_tracking: function(frm, service_provider, shipment_id) {
		let delivery_notes = [];
		(frm.doc.shipment_delivery_note || []).forEach((d) => {
			delivery_notes.push(d.delivery_note);
		});
		frappe.call({
			method: "erpnext.stock.doctype.shipment.shipment.update_tracking",
			freeze: true,
			freeze_message: __("Updating Tracking"),
			args: {
				shipment: frm.doc.name,
				shipment_id: shipment_id,
				service_provider: service_provider,
				delivery_notes: delivery_notes
			},
			callback: function(r) {
				if (!r.exc) {
					frm.reload_doc();
				}
			}
		});
	}
});

frappe.ui.form.on('Shipment Delivery Note', {
	delivery_note: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.delivery_note) {
			let row_index = row.idx - 1;
			if(validate_duplicate(frm, 'shipment_delivery_note', row.delivery_note, row_index)) {
				frappe.throw(__(`You have entered a duplicate Delivery Note on Row ${row.idx}. Please rectify and try again.`));
			}
		}
	},
	grand_total: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];
		if (row.grand_total) {
			var value_of_goods = parseFloat(frm.doc.value_of_goods)+parseFloat(row.grand_total);
			frm.set_value("value_of_goods", Math.round(value_of_goods));
			frm.refresh_fields("value_of_goods");
		}
	},
});

var validate_duplicate =  function(frm, table, fieldname, index){
	return (
		table === 'shipment_delivery_note'
			? frm.doc[table].some((detail, i) => detail.delivery_note === fieldname && !(index === i))
			: frm.doc[table].some((detail, i) => detail.email === fieldname && !(index === i))
	);
};

function select_from_available_services(frm, available_services) {
	var headers = [ __("Service Provider"), __("Carrier"), __("Carrier’s Service"), __("Price"), "" ];
	cur_frm.render_available_services = function(d, headers, data){
		const arranged_data = data.reduce((prev, curr) => {
			if (curr.is_preferred) {
				prev.preferred_services.push(curr);
			} else {
				prev.other_services.push(curr);
			}
			return prev;
		}, { preferred_services: [], other_services: [] });
		d.fields_dict.available_services.$wrapper.html(
			frappe.render_template('shipment_service_selector',
				{'header_columns': headers, 'data': arranged_data}
			)
		);
	};
	const d = new frappe.ui.Dialog({
		title: __("Select Shipment Service to create Shipment"),
		fields: [
			{
				fieldtype:'HTML',
				fieldname:"available_services",
				label: __('Available Services')
			}
		]
	});
	cur_frm.render_available_services(d, headers, available_services);
	let shipment_notific_email = [];
	let tracking_notific_email = [];
	(frm.doc.shipment_notification_subscription || []).forEach((d) => {
		if (!d.unsubscribed) {
			shipment_notific_email.push(d.email);
		}
	});
	(frm.doc.shipment_status_update_subscription || []).forEach((d) => {
		if (!d.unsubscribed) {
			tracking_notific_email.push(d.email);
		}
	});
	let delivery_notes = [];
	(frm.doc.shipment_delivery_note || []).forEach((d) => {
		delivery_notes.push(d.delivery_note);
	});
	cur_frm.select_row = function(service_data){
		frappe.call({
			method: "erpnext.stock.doctype.shipment.shipment.create_shipment",
			freeze: true,
			freeze_message: __("Creating Shipment"),
			args: {
				shipment: frm.doc.name,
				pickup_from_type: frm.doc.pickup_from_type,
				delivery_to_type: frm.doc.delivery_to_type,
				pickup_address_name: frm.doc.pickup_address_name,
				delivery_address_name: frm.doc.delivery_address_name,
				shipment_parcel: frm.doc.shipment_parcel,
				description_of_content: frm.doc.description_of_content,
				pickup_date: frm.doc.pickup_date,
				pickup_contact_name: frm.doc.pickup_from_type === 'Company' ? frm.doc.pickup_contact_person : frm.doc.pickup_contact_name,
				delivery_contact_name: frm.doc.delivery_contact_name,
				value_of_goods: frm.doc.value_of_goods,
				service_data: service_data,
				shipment_notific_email: shipment_notific_email,
				tracking_notific_email: tracking_notific_email,
				delivery_notes: delivery_notes
			},
			callback: function(r) {
				if (!r.exc) {
					frm.reload_doc();
					frappe.msgprint(__("Shipment created with {0}, ID is {1}", [r.message.service_provider, r.message.shipment_id]));
					frm.events.update_tracking(frm, r.message.service_provider, r.message.shipment_id);
				}
			}
		});
		d.hide();
	};
	d.show();
}
