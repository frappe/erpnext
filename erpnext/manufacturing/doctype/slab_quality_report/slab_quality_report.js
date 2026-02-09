frappe.ui.form.on("Slab Quality Report", {
	refresh(frm) {
		frm.trigger('render_visualizer');
	},

	render_visualizer(frm) {
		if (!frm.fields_dict.visualizer_preview) return;
		
		const wrapper = frm.fields_dict.visualizer_preview.$wrapper;
		wrapper.empty();

		if (!frm.doc.slab_template) {
			wrapper.html(`<div class="text-center text-muted p-5">${__("Slab Template not selected")}</div>`);
			return;
		}

        const parts = frm.doc.slab_template.split('-');
        let size_name = parts.length >= 2 ? parts[parts.length - 2] : null;

        if (!size_name) {
             wrapper.html(`<div class="text-center text-muted p-5">${__("Could not determine Slab Size from Template")}</div>`);
             return;
        }

        frappe.db.get_doc('Slab Size', size_name).then(slab_size_doc => {
            const length = slab_size_doc.length; // mm
            const breadth = slab_size_doc.breadth; // mm (width)

            const obs_data = frm.doc.observations || [];
            
            // CSS Variables for styling
            const borderColor = 'var(--text-color)';
            const bgColor = 'var(--fg-color)';
            const markerColor = '#dc3545';

            let markers_html = obs_data.map(obs => {
                const left_pct = (obs.x / length) * 100;
                const top_pct = (obs.y / breadth) * 100;
                
                // Marker
                return `<div class="obs-marker" style="
                    position: absolute;
                    left: ${left_pct}%;
                    top: ${top_pct}%;
                    width: 0;
                    height: 0;
                " title="${obs.x} mm from left & ${obs.y} mm from top">
                    <div style="
                        width: 12px;
                        height: 12px;
                        background: ${markerColor};
                        border: 2px solid white;
                        border-radius: 50%;
                        transform: translate(-50%, -50%);
                        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                        cursor: help;
                    "></div>
                    <div style="
                        position: absolute;
                        left: 12px;
                        top: -10px;
                        background: var(--card-bg);
                        color: var(--text-color);
                        border: 1px solid var(--border-color);
                        padding: 2px 6px;
                        border-radius: 4px;
                        font-size: 11px;
                        white-space: nowrap;
                        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
                        z-index: 10;
                        pointer-events: none;
                    ">${obs.text}</div>
                </div>`;
            }).join('');

            const container_html = `
                <div class="row">
                    <div class="col-12">
                        <div class="visualizer-container position-relative mb-3" style="
                            width: 100%;
                            max-width: 800px;
                            aspect-ratio: ${length} / ${breadth};
                            outline: 2px solid ${borderColor};
                            background: ${bgColor};
                            margin: 0 auto;
                        ">
                            ${markers_html}
                        </div>
                    </div>
                </div>
            `;

            wrapper.html(container_html);
        }).catch(err => {
            console.error(err);
             wrapper.html(`<div class="text-center text-muted p-5">${__("Error fetching Slab Size details")}</div>`);
        });
	}
});
