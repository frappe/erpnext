// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Delivery Trip', {
	setup: function(frm) {
		frm.set_query("address", "delivery_stops", function(doc, cdt, cdn) {
			var row = locals[cdt][cdn];
			if (row.customer) {
				return {
					query: 'frappe.contacts.doctype.address.address.address_query',
					filters: {
						link_doctype: "Customer",
						link_name: row.customer
					}
				};
			}
		})

		frm.set_query("contact", "delivery_stops", function(doc, cdt, cdn) {
			var row = locals[cdt][cdn];
			if (row.customer) {
				return {
					query: 'frappe.contacts.doctype.contact.contact.contact_query',
					filters: {
						link_doctype: "Customer",
						link_name: row.customer
					}
				};
			}
		})
	},

	refresh: function (frm) {
		if (frm.doc.docstatus == 1 && frm.doc.delivery_stops.length > 0) {
			frm.add_custom_button(__("Notify Customers via Email"), function () {
				frm.trigger('notify_customers');
			});
		}
	},

	calculate_arrival_time: function (frm) {
		frappe.call({
			method: 'erpnext.stock.doctype.delivery_trip.delivery_trip.calculate_time_matrix',
			freeze: true,
			freeze_message: __("Updating estimated arrival times."),
			args: {
				name: frm.doc.name
			},
			callback: function (r) {
				if (r.message.error) {
					frappe.throw(__("Malformatted address for {0}, please fix to continue.",
						[r.message.error.destination.address]));
				}
				frm.reload_doc();
			}
		});
	},

	notify_customers: function (frm) {
		var owner_email = frm.doc.owner == "Administrator"
			? frappe.user_info("Administrator").email
			: frm.doc.owner;

		$.each(frm.doc.delivery_stops || [], function (i, delivery_stop) {
			if (!delivery_stop.delivery_notes) {
				frappe.msgprint({
					"message": __("No Delivery Note selected for Customer {}", [delivery_stop.customer]),
					"title": __("Warning"),
					"indicator": "orange",
					"alert": 1
				});
			}
		});
		frappe.confirm(__("Do you want to notify all the customers by email?"), function () {
			frappe.call({
				method: "erpnext.stock.doctype.delivery_trip.delivery_trip.notify_customers",
				args: {
					"docname": frm.doc.name,
					"date": frm.doc.date,
					"driver": frm.doc.driver,
					"vehicle": frm.doc.vehicle,
					"sender_email": owner_email,
					"sender_name": frappe.user.full_name(owner_email),
					"delivery_notification": frm.doc.delivery_notification
				}
			});
			frm.doc.email_notification_sent = true;
			frm.refresh_field('email_notification_sent');
		});
	}
});



frappe.ui.form.on('Delivery Stop', {
	customer: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if(row.customer) {
			frappe.call({
				method: "erpnext.stock.doctype.delivery_trip.delivery_trip.get_contact_and_address",
				args: {"name": row.customer},
				callback: function (r) {
					if (r.message) {
						if (r.message["shipping_address"]) {
							frappe.model.set_value(cdt, cdn, "address", r.message["shipping_address"].parent);
						}
						else {
							frappe.model.set_value(cdt, cdn, "address", '');
						}
						if (r.message["contact_person"]) {
							frappe.model.set_value(cdt, cdn, "contact", r.message["contact_person"].parent);
						}
						else {
							frappe.model.set_value(cdt, cdn, "contact", '');
						}
					}
					else {
						frappe.model.set_value(cdt, cdn, "address", '');
						frappe.model.set_value(cdt, cdn, "contact", '');
					}
				}
			});
		}
	},
	address: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if(row.address) {
			frappe.call({
				method: "frappe.contacts.doctype.address.address.get_address_display",
				args: {"address_dict": row.address},
				callback: function (r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, "customer_address", r.message);
					}
				}
			});
		} else {
			frappe.model.set_value(cdt, cdn, "customer_address", "");
		}
	},

	contact: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if(row.contact) {
			frappe.call({
				method: "erpnext.stock.doctype.delivery_trip.delivery_trip.get_contact_display",
				args: {"contact": row.contact},
				callback: function (r) {
					if (r.message) {
						frappe.model.set_value(cdt, cdn, "customer_contact", r.message);
					}
				}
			});
		} else {
			frappe.model.set_value(cdt, cdn, "customer_contact", "");
		}
	},

	select_delivery_notes: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		frappe.call({
			method: "erpnext.stock.doctype.delivery_trip.delivery_trip.get_delivery_notes",
			args: {"customer": row.customer},
			callback: function (r) {
				var delivery_notes = [];
				$.each(r.message, function (field, value) {
					delivery_notes.push(value.name);
				});
				if (r.message) {
					var d = new frappe.ui.Dialog({
						title: __("Select Delivery Notes"),
						fields: [{fieldtype: "HTML", fieldname: "delivery_notes_html"}]
					});
					var html = $(`
						<div style="border: 1px solid #d1d8dd">
							<div class="list-item list-item--head">
								<div class="list-item__content list-item__content--flex-2">
									${__('Delivery Notes')}
								</div>
							</div>
							${delivery_notes.map(delivery_note => `
								<div class="list-item">
									<div class="list-item__content list-item__content--flex-2">
										<label>
										<input type="checkbox" data-delivery-note="${delivery_note}" checked="checked"/>
										${delivery_note}
										</label>
									</div>
								</div>
							`).join("")}
						</div>
					`);

					var delivery_notes_el = d.fields_dict.delivery_notes_html.$wrapper.html(html);

					d.set_primary_action(__("Select"), function () {
						var delivery_notes = delivery_notes_el.find('input[type=checkbox]:checked')
							.map((i, el) => $(el).attr('data-delivery-note')).toArray();
						if (!delivery_notes) return;
						frappe.model.set_value(cdt, cdn, "delivery_notes", delivery_notes.join(","));
						d.hide();
					});
					d.show();
				}
				else {
					frappe.msgprint(__("No submitted Delivery Notes found"));
				}
			}
		});
	}
});