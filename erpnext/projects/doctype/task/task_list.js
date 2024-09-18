frappe.listview_settings["Task"] = {
	add_fields: [
		"project",
		"status",
		"priority",
		"exp_start_date",
		"exp_end_date",
		"subject",
		"progress",
		"depends_on_tasks",
	],
	filters: [["status", "=", "Open"]],
	onload: function (listview) {
		var method = "erpnext.projects.doctype.task.task.set_multiple_status";

		listview.page.add_menu_item(__("Set as Open"), function () {
			listview.call_for_selected_items(method, { status: "Open" });
		});

		listview.page.add_menu_item(__("Set as Completed"), function () {
			listview.call_for_selected_items(method, { status: "Completed" });
		});
	},
	get_indicator: function (doc) {
		var colors = {
			Open: "orange",
			Overdue: "red",
			"Pending Review": "orange",
			Working: "orange",
			Completed: "green",
			Cancelled: "dark grey",
			Template: "blue",
		};
		return [__(doc.status), colors[doc.status], "status,=," + doc.status];
	},
	gantt_custom_popup_html: function (ganttobj, task) {
		let html = `
			<a class="text-white mb-2 inline-block cursor-pointer"
				href="/app/task/${ganttobj.id}"">
				${ganttobj.name}
			</a>
		`;

		if (task.project) {
			html += `<p class="mb-1">${__("Project")}:
				<a class="text-white inline-block"
					href="/app/project/${task.project}"">
					${task.project}
				</a>
			</p>`;
		}
		html += `<p class="mb-1">
			${__("Progress")}:
			<span class="text-white">${ganttobj.progress}%</span>
		</p>`;

		if (task._assign) {
			const assign_list = JSON.parse(task._assign);
			const assignment_wrapper = `
				<span>Assigned to:</span>
				<span class="text-white">
					${assign_list.map((user) => frappe.user_info(user).fullname).join(", ")}
				</span>
			`;
			html += assignment_wrapper;
		}

		return `<div class="p-3" style="min-width: 220px">${html}</div>`;
	},
    refresh: function (listview) {
        listview.page.add_inner_button(__("Print"), () => {
			
            const ganttChartSVG1 = document.querySelector('.gantt');
            if (ganttChartSVG) {
                svgExport.downloadPdf(
                    ganttChartSVG1,
                    "Gantt Export"
                );
            }
			return;
			// Create a new window for printing
			const printWindow = window.open('', '', 'width=800,height=600');
			printWindow.document.open();
			printWindow.document.write('Gantt Chart');
			printWindow.document.write('');
			// Custom styles for the Gantt chart
			printWindow.document.write( /* Your custom CSS styles for the Gantt chart go here */ );
			printWindow.document.write('');
			
			const ganttChartSVG = document.querySelector('.gantt');
			const bbox = ganttChartSVG.getBBox();
			const serializer = new XMLSerializer();
			const svgXml = serializer.serializeToString(ganttChartSVG);
			
			// Modify the SVG content to set a white background and adjust the viewBox
			const modifiedSvgXml = svgXml.replace(
				'<svg',
				`<svg style="background-color: white !important;" width="${bbox.width}" height="${bbox.height}" viewBox="${bbox.x} ${bbox.y} ${bbox.width} ${bbox.height}"`
			);
			
			// Add the modified SVG content to the print window
			printWindow.document.write(modifiedSvgXml);
			
			// Close the print window after printing
			printWindow.document.write('</body></html>');
			printWindow.document.close();
			printWindow.print();
			printWindow.close();
        })
    }
};
