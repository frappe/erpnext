// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Quality Control Lot", {
	render_serial_numbers(frm) {
		frm.toggle_display("serial_numbers_section", false);
		if (frm.is_new()) return;

		const wrapper = frm.get_field("serial_numbers_html").$wrapper;
		wrapper.empty();

		if (frm.doc.batch_no) {
			frappe.call({
				method: "erpnext.stock.doctype.quality_control_lot.quality_control_lot.get_batch_summary",
				args: { lot_name: frm.doc.name },
				callback: (r) => {
					const summary = r.message;
					if (!summary) return;

					const matches = summary.held_qty === summary.expected_qty;
					const balance = matches
						? `<span class="indicator-pill green">${__("In Quarantine: {0}", [
								summary.held_qty,
							])}</span>`
						: `<span class="indicator-pill orange">${__(
								"In Quarantine: {0} (lot expects {1})",
								[summary.held_qty, summary.expected_qty]
							)}</span>`;
					wrapper.prepend(`
						<p>${__("Batch")} ${frappe.utils.get_form_link(
							"Batch",
							summary.batch_no,
							true
						)} &nbsp; ${balance}</p>`);
					frm.toggle_display("serial_numbers_section", true);
				},
			});
		}

		frappe.call({
			method: "erpnext.stock.doctype.quality_control_lot.quality_control_lot.get_serial_numbers",
			args: { lot_name: frm.doc.name },
			callback: (r) => {
				const serials = r.message || [];
				if (!serials.length) return;

				const state_colors = {
					"In Quarantine": "orange",
					Released: "green",
					"Rejected Stock": "red",
					Returned: "gray",
				};
				const rows = serials
					.map((row) => {
						const verdict = row.verdict
							? `<span class="indicator-pill ${
									row.verdict === "Accepted" ? "green" : "red"
								}">${__(row.verdict)}</span>`
							: "";
						const warehouse = row.warehouse
							? frappe.utils.get_form_link("Warehouse", row.warehouse, true)
							: "";
						return `<tr>
							<td>${frappe.utils.get_form_link("Serial No", row.serial_no, true)}</td>
							<td>${verdict}</td>
							<td>${warehouse}</td>
							<td><span class="indicator-pill ${state_colors[row.state] || "gray"}">${__(
								row.state
							)}</span></td>
						</tr>`;
					})
					.join("");

				wrapper.append(`
					<table class="table table-bordered table-sm">
						<thead>
							<tr>
								<th>${__("Serial No")}</th>
								<th>${__("Verdict")}</th>
								<th>${__("Current Warehouse")}</th>
								<th>${__("State")}</th>
							</tr>
						</thead>
						<tbody>${rows}</tbody>
					</table>`);
				frm.toggle_display("serial_numbers_section", true);
			},
		});
	},

	setup(frm) {
		frm.set_query("batch_no", function (doc) {
			return { filters: { item: doc.item_code } };
		});
	},

	refresh(frm) {
		frm.trigger("render_serial_numbers");

		if (!frm.is_new() && frm.doc.pending_qty > 0 && !frm.doc.quality_inspection) {
			frm.add_custom_button(__("Create Quality Inspection"), () => {
				frappe.new_doc("Quality Inspection", {
					inspection_type: "Incoming",
					reference_type: "Quality Control Lot",
					reference_name: frm.doc.name,
					item_code: frm.doc.item_code,
					batch_no: frm.doc.batch_no,
					inspection_basis: frm.doc.inspection_basis,
					sample_size: frm.doc.inspection_basis === "Each Quantity" ? 0 : frm.doc.pending_qty,
					quality_inspection_template: frm.doc.inspection_template,
				});
			});
		}

		if (frm.doc.quality_inspection) {
			frm.add_custom_button(__("Open Quality Inspection"), () => {
				frappe.set_route("Form", "Quality Inspection", frm.doc.quality_inspection);
			});
		}

		const rejected_outstanding =
			flt(frm.doc.rejected_qty) - flt(frm.doc.returned_qty) - flt(frm.doc.disposed_qty);
		if (rejected_outstanding > 0) {
			if (
				["Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"].includes(
					frm.doc.source_document_type
				)
			) {
				frm.add_custom_button(__("Create Purchase Return"), () => {
					frappe.call({
						method: "erpnext.stock.services.quality_quarantine.make_purchase_return_for_lot",
						args: { lot_name: frm.doc.name },
						freeze: true,
						callback: (r) => {
							const doc = frappe.model.sync(r.message)[0];
							frappe.set_route("Form", doc.doctype, doc.name);
						},
					});
				});
			}

			frm.add_custom_button(__("Move Rejected Stock Out"), () => {
				frappe.call({
					method: "erpnext.stock.services.quality_quarantine.make_rejected_stock_transfer_for_lot",
					args: { lot_name: frm.doc.name },
					freeze: true,
					callback: (r) => {
						const doc = frappe.model.sync(r.message)[0];
						frappe.set_route("Form", doc.doctype, doc.name);
					},
				});
			});
		}
	},
});
