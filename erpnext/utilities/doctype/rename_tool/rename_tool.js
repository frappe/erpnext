// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.ui.form.on("Rename Tool", {
	onload: function (frm) {
		return frappe.call({
			method: "erpnext.utilities.doctype.rename_tool.rename_tool.get_doctypes",
			callback: function (r) {
				frm.set_df_property("select_doctype", "options", r.message);
			},
		});
	},
	refresh: function (frm) {
		frm.disable_save();

		frm.get_field("file_to_rename").df.options = {
			restrictions: {
				allowed_file_types: [".csv"],
			},
		};
<<<<<<< HEAD

		frm.trigger("render_overview");

		frm.page.set_primary_action(__("Rename"), function () {
=======
		if (!frm.doc.file_to_rename) {
			frm.get_field("rename_log").$wrapper.html("");
		}
		frm.page.set_primary_action(__("Rename"), function () {
			frm.get_field("rename_log").$wrapper.html("<p>Renaming...</p>");
>>>>>>> 7c4cf3e834 (Favicon.svg)
			frappe.call({
				method: "erpnext.utilities.doctype.rename_tool.rename_tool.upload",
				args: {
					select_doctype: frm.doc.select_doctype,
				},
<<<<<<< HEAD
				freeze: true,
				freeze_message: __("Scheduling..."),
				callback: function () {
					frappe.msgprint({
						message: __("Rename jobs for doctype {0} have been enqueued.", [
							frm.doc.select_doctype,
						]),
						alert: true,
						indicator: "green",
					});
					frm.set_value("select_doctype", "");
					frm.set_value("file_to_rename", "");

					frm.trigger("render_overview");
				},
				error: function (r) {
					frappe.msgprint({
						message: __("Rename jobs for doctype {0} have not been enqueued.", [
							frm.doc.select_doctype,
						]),
						alert: true,
						indicator: "red",
					});

					frm.trigger("render_overview");
=======
				callback: function (r) {
					let html = r.message.join("<br>");

					if (r.exc) {
						r.exc = frappe.utils.parse_json(r.exc);
						if (Array.isArray(r.exc)) {
							html += "<br>" + r.exc.join("<br>");
						}
					}

					frm.get_field("rename_log").$wrapper.html(html);
>>>>>>> 7c4cf3e834 (Favicon.svg)
				},
			});
		});
	},
<<<<<<< HEAD
	render_overview: function (frm) {
		frappe.db
			.get_list("RQ Job", { filters: { status: ["in", ["started", "queued", "finished", "failed"]] } })
			.then((jobs) => {
				let counts = {
					started: 0,
					queued: 0,
					finished: 0,
					failed: 0,
				};

				for (const job of jobs) {
					if (job.job_name !== "frappe.model.rename_doc.bulk_rename") {
						continue;
					}

					counts[job.status]++;
				}

				frm.get_field("rename_log").$wrapper.html(`
					<p><strong>${__("Bulk Rename Jobs")}</a></strong></p>
					<p><a href="/app/rq-job?queue=long&status=queued">${__("Queued")}: ${counts.queued}</a></p>
					<p><a href="/app/rq-job?queue=long&status=started">${__("Started")}: ${counts.started}</a></p>
					<p><a href="/app/rq-job?queue=long&status=finished">${__("Finished")}: ${counts.finished}</a></p>
					<p><a href="/app/rq-job?queue=long&status=failed">${__("Failed")}: ${counts.failed}</a></p>
				`);
			});
	},
=======
>>>>>>> 7c4cf3e834 (Favicon.svg)
});
