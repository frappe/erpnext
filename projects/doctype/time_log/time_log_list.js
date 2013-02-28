// render
wn.listview_settings['Time Log'] = {
	selectable: true,
	onload: function(me) {
		me.appframe.add_button(wn._("Make Time Log Batch"), function() {
			var selected = me.get_checked_items() || [];

			if(!selected.length) {
				msgprint(wn._("Please select Time Logs."))
			}
			
			// select only billable time logs
			for(var i in selected) {
				var d = selected[i];
				if(!d.billable) {
					msgprint(wn._("Time Log is not billable") + ": " + d.name);
					return;
				}
				if(d.sales_invoice) {
					msgprint(wn._("Time Log has been Invoiced") + ": " + d.name);
				}
			}
			
			//
			
		}, "icon-file-alt");
	}
};
