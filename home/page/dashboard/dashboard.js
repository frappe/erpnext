// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <http://www.gnu.org/licenses/>.

pscript.onload_dashboard = function() {
	// load jqplot
	wn.require('lib/js/lib/jqplot/css/jqplot.css');
	wn.require('lib/js/lib/jqplot/jquery.jqplot.min.js');
	wn.require('lib/js/lib/jqplot/jqplot-plugins/jqplot.barRenderer.js'); 
	wn.require('lib/js/lib/jqplot/jqplot-plugins/jqplot.canvasAxisTickRenderer.min.js');
	wn.require('lib/js/lib/jqplot/jqplot-plugins/jqplot.canvasTextRenderer.min.js');
	wn.require('lib/js/lib/jqplot/jqplot-plugins/jqplot.categoryAxisRenderer.min.js');


	pscript.dashboard_settings = {
		company: sys_defaults.company,
		start: (function() {
			var start_date = dateutil.add_days(new Date(), -180);
			var year_start_date = dateutil.str_to_obj(sys_defaults.year_start_date);
			if (start_date < year_start_date) { start_date = year_start_date; }
			console.log(start_date);
			return dateutil.obj_to_str(start_date);
		})(),
		end: (function() {
			var end_date = new Date();
			var year_end_date = dateutil.str_to_obj(sys_defaults.year_end_date);
			if (end_date > year_end_date) { end_date = year_end_date; }
			console.log(end_date);
			return dateutil.obj_to_str(end_date);
		})(),
		interval: 30
	}
	
	var ph = new PageHeader($('.dashboard .header').get(0), 'Dashboard');
	var db = new Dashboard();

	ph.add_button('Settings', db.show_settings);
	
	db.refresh();
	
}

Dashboard = function() {
	var me = this;
	$.extend(me, {
		refresh: function() {
			$('.dashboard .help_box').css('display', 'block');
			$c_page('home', 'dashboard', 'load_dashboard', JSON.stringify(pscript.dashboard_settings), function(r,rt) {
				$('.dashboard .help_box').css('display', 'none');
				me.render(r.message);
			})			
		},
		
		render: function(data) {
			$('.dashboard_table').html('');
			var t = make_table($('.dashboard_table').get(0), 4, 2, '100%', ['50%', '50%'], {padding: '5px'});
			var ridx=0; var cidx=0;
			for(var i=0; i< data.length; i++) {
				// switch columns and rows
				if(cidx==2) { cidx=0; ridx++}
				
				// give an id!
				var cell = $td(t,ridx,cidx);
				var title = $a(cell, 'div', 'dashboard-title', '', data[i][0].title);
				var parent = $a(cell, 'div', 'dashboard-graph');
				if(data[i][0].comment);
					var comment = $a(cell, 'div', 'comment', '', data[i][0].comment)
				
				parent.id = '_dashboard' + ridx + '-' + cidx;
				
				// render graph
				me.render_graph(parent.id, data[i][1], data[i][0].fillColor);
				cidx++;
			}
		},
		
		render_graph: function(parent, values, fillColor) {
			var vl = [];
			$.each(values, function(i,v) { 
				vl.push([dateutil.str_to_user(v[0]), v[1]]);
			});
			$.jqplot(parent, [vl], {
				seriesDefaults:{
					renderer:$.jqplot.BarRenderer,
					rendererOptions: {fillToZero: true},
				},
				axes: {
					// Use a category axis on the x axis and use our custom ticks.
					xaxis: {
						min: 0,
						renderer: $.jqplot.CategoryAxisRenderer,
						tickRenderer: $.jqplot.CanvasAxisTickRenderer,
						tickOptions: {
							angle: -30,
							fontSize: '8pt'
						}
					},
					// Pad the y axis just a little so bars can get close to, but
					// not touch, the grid boundaries.  1.2 is the default padding.
					yaxis: {
						min: 0,
						pad: 1.05,
						tickOptions: {formatString: '%d'}
					}
				},
				seriesColors: [fillColor]
			});
		},
		
		show_settings: function() {
			var d = new wn.widgets.Dialog({
				title: 'Set Company Settings',
				width: 500,
				fields: [
					{
						label:'Company', 
						reqd: 1,
						fieldname:'company', 
						fieldtype:'Link',
						options: 'Company'
					},
					{
						label:'Start Date', 
						reqd: 1,
						fieldname:'start', 
						fieldtype:'Date',
					},
					{
						label:'End Date', 
						reqd: 1,
						fieldname:'end', 
						fieldtype:'Date',
					},
					{
						label:'Interval', 
						reqd: 1,
						fieldname:'interval', 
						fieldtype:'Int'
					},
					{
						label:'Regenerate', 
						fieldname:'refresh', 
						fieldtype:'Button'
					}
				]
			});
			d.onshow = function() {
				d.set_values(pscript.dashboard_settings);
			}
			d.fields_dict.refresh.input.onclick = function() {
				pscript.dashboard_settings = d.get_values();
				me.refresh();
				d.hide();
			}
			d.show();
		}
	})
}
