// Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on("Preliminary Quality Check", {
	refresh(frm) {
		frm.trigger("render_visual_bend_report");
	},

	h_bend(frm) {
		frm.trigger("render_visual_bend_report");
	},

	v_bend(frm) {
		frm.trigger("render_visual_bend_report");
	},

	d1_bend(frm) {
		frm.trigger("render_visual_bend_report");
	},

	d2_bend(frm) {
		frm.trigger("render_visual_bend_report");
	},

	render_visual_bend_report(frm) {
		const wrapper = frm.fields_dict.visual_bend_report.wrapper;
		const measurements = {
			v_bend: frm.doc.v_bend || 0,
			h_bend: frm.doc.h_bend || 0,
			d1_bend: frm.doc.d1_bend || 0,
			d2_bend: frm.doc.d2_bend || 0,
		};

		$(wrapper).html(`
			<div class="d-flex flex-column align-items-center">
				<div class="measurement-card w-100 p-5 mb-4 d-flex flex-column align-items-center">
					<div class="measure-wrapper position-relative" style="width: 600px; height: 350px;">
						<!-- SVG Diagram -->
						<svg width="100%" height="100%" viewBox="0 0 600 350" preserveAspectRatio="none">
							<!-- Border -->
							<rect x="2" y="2" width="596" height="346" fill="none" class="stroke-default"
								stroke-width="3" />

							<!-- Diagonals -->
							<line x1="2" y1="2" x2="598" y2="348" class="stroke-default" stroke-width="2" />
							<line x1="2" y1="348" x2="598" y2="2" class="stroke-default" stroke-width="2" />

							<!-- Vertical Line at ~33% -->
							<line x1="200" y1="2" x2="200" y2="348" class="stroke-default" stroke-width="2" />

							<!-- Horizontal Center Line from Vertical Line to Right Edge -->
							<line x1="2" y1="175" x2="598" y2="175" class="stroke-default" stroke-width="2" />
						</svg>

						<!-- Values -->
						<!-- Vertical Bend -->
						<div class="input-pos" style="left: 200px; top: 60px;">
							<span class="bend-value badge badge-secondary">${measurements.v_bend}</span>
						</div>

						<!-- Horizontal Bend -->
						<div class="input-pos" style="left: 80px; top: 175px;">
							<span class="bend-value badge badge-secondary">${measurements.h_bend}</span>
						</div>

						<!-- TR Diagonal Bend -->
						<div class="input-pos" style="left: 480px; top: 70px;">
							<span class="bend-value badge badge-secondary">${measurements.d2_bend}</span>
						</div>

						<!-- BR Diagonal Bend -->
						<div class="input-pos" style="left: 480px; top: 280px;">
							<span class="bend-value badge badge-secondary">${measurements.d1_bend}</span>
						</div>
					</div>
				</div>
			</div>
			<style>
				.stroke-default {
					stroke: var(--text-color);
				}
				.input-pos {
					position: absolute;
					transform: translate(-50%, -50%);
				}
				.bend-value {
					font-size: 1.2em;
					padding: 5px 10px;
				}
				.measurement-card {
					background: var(--card-bg, #fff);
					border-radius: 8px;
					/* box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); */
					border: 1px solid var(--border-color);
				}
			</style>
		`);
	},
});
