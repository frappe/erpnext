frappe.provide("erpnext.accounts");

erpnext.accounts.unreconcile_payment = {
	add_unreconcile_btn(frm) {
		if (frm.doc.docstatus == 1) {
			if (
<<<<<<< HEAD
				(frm.doc.doctype == "Journal Entry" &&
					!["Journal Entry", "Bank Entry", "Cash Entry"].includes(frm.doc.voucher_type)) ||
=======
				(frm.doc.doctype == "Journal Entry" && frm.doc.voucher_type != "Journal Entry") ||
>>>>>>> 7c4cf3e834 (Favicon.svg)
				!["Purchase Invoice", "Sales Invoice", "Journal Entry", "Payment Entry"].includes(
					frm.doc.doctype
				)
			) {
				return;
			}

			frappe.call({
				method: "erpnext.accounts.doctype.unreconcile_payment.unreconcile_payment.doc_has_references",
				args: {
					doctype: frm.doc.doctype,
					docname: frm.doc.name,
				},
				callback: function (r) {
					if (r.message) {
						frm.add_custom_button(
							__("UnReconcile"),
							function () {
								erpnext.accounts.unreconcile_payment.build_unreconcile_dialog(frm);
							},
							__("Actions")
						);
					}
				},
			});
		}
	},

	build_selection_map(frm, selections) {
		// assuming each row is an individual voucher
		// pass this to server side method that creates unreconcile doc for each row
		let selection_map = [];
		if (["Sales Invoice", "Purchase Invoice"].includes(frm.doc.doctype)) {
			selection_map = selections.map(function (elem) {
				return {
					company: elem.company,
<<<<<<< HEAD
					voucher_type: elem.reference_doctype,
					voucher_no: elem.reference_name,
=======
					voucher_type: elem.voucher_type,
					voucher_no: elem.voucher_no,
>>>>>>> 7c4cf3e834 (Favicon.svg)
					against_voucher_type: frm.doc.doctype,
					against_voucher_no: frm.doc.name,
				};
			});
		} else if (["Payment Entry", "Journal Entry"].includes(frm.doc.doctype)) {
			selection_map = selections.map(function (elem) {
				return {
					company: elem.company,
					voucher_type: frm.doc.doctype,
					voucher_no: frm.doc.name,
<<<<<<< HEAD
					against_voucher_type: elem.reference_doctype,
					against_voucher_no: elem.reference_name,
=======
					against_voucher_type: elem.voucher_type,
					against_voucher_no: elem.voucher_no,
>>>>>>> 7c4cf3e834 (Favicon.svg)
				};
			});
		}
		return selection_map;
	},

	build_unreconcile_dialog(frm) {
		if (
			["Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry"].includes(frm.doc.doctype)
		) {
			let child_table_fields = [
				{
					label: __("Voucher Type"),
<<<<<<< HEAD
					fieldname: "reference_doctype",
					fieldtype: "Link",
=======
					fieldname: "voucher_type",
					fieldtype: "Dynamic Link",
>>>>>>> 7c4cf3e834 (Favicon.svg)
					options: "DocType",
					in_list_view: 1,
					read_only: 1,
				},
				{
					label: __("Voucher No"),
<<<<<<< HEAD
					fieldname: "reference_name",
					fieldtype: "Dynamic Link",
					options: "reference_doctype",
=======
					fieldname: "voucher_no",
					fieldtype: "Link",
					options: "voucher_type",
>>>>>>> 7c4cf3e834 (Favicon.svg)
					in_list_view: 1,
					read_only: 1,
				},
				{
					label: __("Allocated Amount"),
					fieldname: "allocated_amount",
					fieldtype: "Currency",
					in_list_view: 1,
					read_only: 1,
					options: "account_currency",
				},
<<<<<<< HEAD
				{
					label: __("Currency"),
					fieldname: "account_currency",
					fieldtype: "Link",
					options: "Currency",
					read_only: 1,
				},
=======
				{ label: __("Currency"), fieldname: "account_currency", fieldtype: "Currency", read_only: 1 },
>>>>>>> 7c4cf3e834 (Favicon.svg)
			];
			let unreconcile_dialog_fields = [
				{
					label: __("Allocations"),
					fieldname: "allocations",
					fieldtype: "Table",
					read_only: 1,
					fields: child_table_fields,
<<<<<<< HEAD
					cannot_add_rows: true,
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
				},
			];

			// get linked payments
			frappe.call({
				method: "erpnext.accounts.doctype.unreconcile_payment.unreconcile_payment.get_linked_payments_for_doc",
				args: {
					company: frm.doc.company,
					doctype: frm.doc.doctype,
					docname: frm.doc.name,
				},
				callback: function (r) {
					if (r.message) {
						// populate child table with allocations
						unreconcile_dialog_fields[0].data = r.message;
						unreconcile_dialog_fields[0].get_data = function () {
							return r.message;
						};

						let d = new frappe.ui.Dialog({
<<<<<<< HEAD
							title: __("UnReconcile Allocations"),
							fields: unreconcile_dialog_fields,
							size: "large",
							primary_action_label: __("UnReconcile"),
=======
							title: "UnReconcile Allocations",
							fields: unreconcile_dialog_fields,
							size: "large",
							cannot_add_rows: true,
							primary_action_label: "UnReconcile",
>>>>>>> 7c4cf3e834 (Favicon.svg)
							primary_action(values) {
								let selected_allocations = values.allocations.filter((x) => x.__checked);
								if (selected_allocations.length > 0) {
									let selection_map =
										erpnext.accounts.unreconcile_payment.build_selection_map(
											frm,
											selected_allocations
										);
									erpnext.accounts.unreconcile_payment.create_unreconcile_docs(
										selection_map
									);
									d.hide();
								} else {
<<<<<<< HEAD
									frappe.msgprint(__("No Selection"));
=======
									frappe.msgprint("No Selection");
>>>>>>> 7c4cf3e834 (Favicon.svg)
								}
							},
						});

						d.show();
					}
				},
			});
		}
	},

	create_unreconcile_docs(selection_map) {
		frappe.call({
			method: "erpnext.accounts.doctype.unreconcile_payment.unreconcile_payment.create_unreconcile_doc_for_selection",
			args: {
				selections: selection_map,
			},
		});
	},
};
