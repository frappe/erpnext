pscript.queries_bg_dict = {
	'Urgent':'RED',
	'High':'ORANGE',
	'Low':'BLUE',
	'Closed':'GREEN',
	'Pending Review':'YELLOW'
}

pscript.onload_Projects = function() {
	var d = $i('projects_div');
	
	new PageHeader(d, 'Gantt Chart');
	new GanttChart($a(d, 'div', '', { margin:'16px'}));
}


// Gantt Chart
// ==========================================================================

GanttChart = function(parent) {
	this.wrapper = $a(parent, 'div');
	//this.head = new PageHeader(this.wrapper, 'Gantt Chart');

	this.toolbar_area = $a(this.wrapper, 'div','',{padding:'16px', border:'1px solid #AAF', }); $bg(this.toolbar_area, '#EEF'); $br(this.toolbar_area, '3px');
	this.toolbar_tab = make_table(this.toolbar_area, 1, 4, '100%', ['25%', '25%','25%', '25%']);
	this.grid_area = $a(this.wrapper, 'div', '', {margin: '16px 0px'});
	this.no_task_message = $a(this.wrapper, 'div', 'help_box', 
		{textAign:'center', fontSize:'14px'}, 'Select your criteria and click on "Make" to show the Gantt Chart')

	this.get_init_data();
	//this.make_grid();
}

GanttChart.prototype.get_init_data = function() {
	var me = this;
	var callback = function(r,rt) {
		me.pl = r.message.pl.sort();
		me.rl = r.message.rl.sort();

		me.make_toolbar();
	}
	$c_obj('Project Control','get_init_data','', callback);
}

GanttChart.prototype.make_filter = function(label, idx) {
	var w = $a($td(this.toolbar_tab,0,idx), 'div','',{marginBottom:'8px'});
	var l = $a(w, 'div','',{fontSize:'11px'}); l.innerHTML = label;
	return w;
}

GanttChart.prototype.make_select = function(label, options,idx) {
	var w = this.make_filter(label,idx);
	var s = $a(w, 'select','',{width:'100px'}); add_sel_options(s, add_lists(['All'],options));
	return s;
}

GanttChart.prototype.make_date = function(label,idx) {
	var w = this.make_filter(label,idx);
	var i = $a(w, 'input');

	var user_fmt = locals['Control Panel']['Control Panel'].date_format;
	if(!this.user_fmt)this.user_fmt = 'dd-mm-yy';

	$(i).datepicker({
		dateFormat: user_fmt.replace('yyyy','yy'), 
		altFormat:'yy-mm-dd', 
		changeYear: true
	});
	
	return i;
}

GanttChart.prototype.make_toolbar = function() {

	// resource / project
	this.r_sel = this.make_select('Resource', this.rl, 0);
	this.p_sel = this.make_select('Project', this.pl, 1);
	
	// start / end
	this.s_date = this.make_date('Start Date', 2); this.s_date.value = date.str_to_user(date.month_start());
	this.e_date = this.make_date('End Date', 3); this.e_date.value = date.str_to_user(date.month_end());
	
	// button
	var me = this;
	$btn(this.toolbar_area, 'Make', function() { me.refresh(); }, null, 'green', 1);
	this.print_btn = $btn(this.toolbar_area, 'Print', function() { me.print(); }, {display:'none'},null);
}

GanttChart.prototype.print = function() {
	$(this.grid_area).printElement();
}

GanttChart.prototype.get_data = function() {
	var me = this;
	var callback = function(r, rt) {
		me.tasks = r.message;
		if(me.tasks.length) {
			$dh(me.no_task_message);
			$ds(me.grid_area);
			me.show_tasks(); 
			$di(me.print_btn);
		} else {
			// nothign to show
			$dh(me.grid_area);
			$ds(me.no_task_message);
			$dh(me.print_btn);
			me.no_task_message.innerHTML = 'Nothing allocated for the above criteria'
		}			
	}
	$c_obj('Project Control','get_tasks',
		[date.user_to_str(this.s_date.value), 
		date.user_to_str(this.e_date.value), 
		sel_val(this.p_sel), 
		sel_val(this.r_sel)].join('~~~')
	, callback)
}

GanttChart.prototype.make_grid = function() {
	// clear earlier chart
	this.grid_area.innerHTML = '';
	this.grid = new GanttGrid(this, this.s_date.value, this.e_date.value);
}

GanttChart.prototype.refresh = function() {
	this.get_data();
}
	
GanttChart.prototype.show_tasks = function() {
	this.make_grid();
	for(var i=0; i<this.tasks.length; i++) {
		new GanttTask(this.grid, this.tasks[i], i)
	}
}

// ==========================================================================

GanttGrid = function(chart, s_date, e_date) {
	this.chart = chart;
	this.s_date = s_date;

	this.wrapper = $a(chart.grid_area, 'div');
	this.start_date = date.str_to_obj(date.user_to_str(s_date));
	this.end_date = date.str_to_obj(date.user_to_str(e_date));

	this.n_days = date.get_diff(this.end_date, this.start_date) + 1;	
	this.g_width = 100 / this.n_days + '%';	

	this.make();
}

GanttGrid.prototype.make_grid = function() {
	// grid -----------
	var ht = this.chart.tasks.length * 40 + 'px';
	this.grid = $a($td(this.body, 0, 1), 'div', '', {border:'2px solid #888', height: ht, position:'relative'});	

	this.grid_tab = make_table(this.grid, 1, this.n_days, '100%', [], {width:this.g_width, borderLeft:'1px solid #DDD', height: ht});
	$y(this.grid_tab,{tableLayout:'fixed'});

	this.task_area = $a(this.grid, 'div', '', {position:'absolute', height:ht, width: '100%', top:'0px'});
}

GanttGrid.prototype.make_labels = function() {
	// labels ------------
	this.x_labels = $a($td(this.body, 0, 1), 'div', '', {marginTop:'8px'});	
	this.x_lab_tab = make_table(this.x_labels, 1, this.n_days, '100%', [], {width:this.g_width, fontSize:'10px'});
	$y(this.x_lab_tab,{tableLayout:'fixed'});
	
	var d = this.start_date;
	var today = new Date();
	for(var i=0; i<this.n_days; i++) {
		if(d.getDay()==0) {
			$td(this.x_lab_tab,0,i).innerHTML = d.getDate() + '-' + month_list[d.getMonth()];
			$y($td(this.grid_tab,0,i),{borderLeft:'1px solid RED'})
		}
		if(d.getDate()==today.getDate() && d.getMonth()==today.getMonth() && d.getYear() == today.getYear()) {
			$y($td(this.grid_tab,0,i),{borderLeft:'2px solid #000'})
		}
		var d = date.add_days(this.start_date, 1);
	}
	this.start_date = date.str_to_obj(date.user_to_str(this.s_date));
}

GanttGrid.prototype.make = function() {
	this.body = make_table(this.wrapper, 1, 2, '100%', ['30%','70%']);
	this.make_grid();
	this.make_labels();
	this.y_labels = $a($td(this.body, 0, 0), 'div', '', {marginTop:'2px', position:'relative'});	
}

GanttGrid.prototype.get_x = function(dt) {
	var d = date.str_to_obj(dt); // convert to obj
	return flt(date.get_diff(d, this.start_date)+1) / flt(date.get_diff(this.end_date, this.start_date)+1) * 100;
}

// ==========================================================================

GanttTask = function(grid, data, idx) {
	// start_date, end_date, name, status
	this.start_date = data[3];
	this.end_date = data[4];

	// label
	this.label = $a(grid.y_labels, 'div', '', {'top':(idx*40) + 'px', overflow:'hidden', position:'absolute', 'width':'100%', height: '40px'});
	var l1 = $a($a(this.label, 'div'), 'span', 'link_type'); l1.innerHTML = data[0]; l1.dn = data[7]; l1.onclick = function() { loaddoc('Ticket', this.dn) };
	var l2 = $a(this.label, 'div', '', {fontSize:'10px'}); l2.innerHTML = data[1];

	// bar
	var col = pscript.queries_bg_dict[data[5]];
	if(data[6]!='Open') col = pscript.queries_bg_dict[data[6]];
	if(!col) col = 'BLUE';
	
	this.body = $a(grid.task_area, 'div','',{backgroundColor:col, height:'12px', position:'absolute'});

	//bar info
	this.body_info = $a(this.body, 'div','',{backgroundColor:'#CCC', position:'absolute', zIndex:20});

	var x1 = grid.get_x(this.start_date);
	var x2 = grid.get_x(this.end_date);

	if(x1<=0)x1=0;
	else x1 -=100/flt(date.get_diff(grid.end_date, grid.start_date)+1);
	if(x2>=100)x2=100;
//	else x2+=100/flt(date.get_diff(grid.end_date, grid.start_date)+1);
	
	$y(this.body, { 
		top: idx * 40 + 14 + 'px',
		left: x1 + '%',
		width: (x2-x1) + '%',
		zIndex: 1,
		cursor:'pointer'
	})
	
	// divider
	if(idx) {
		var d1 = $a(grid.task_area, 'div','',{borderBottom: '1px solid #AAA', position:'absolute', width:'100%', top:(idx*40) + 'px'});
		var d2 = $a(grid.y_labels, 'div','',{borderBottom: '1px solid #AAA', position:'absolute', width:'100%', top:(idx*40) + 'px'});
	}
	
	this.make_tooltip(data);
}

GanttTask.prototype.make_tooltip = function(d) {
	var t = '<div>';
	if(d[0]) t += '<b>Task: </b>' + d[0];
	if(d[5]) t += '<br><b>Priority: </b>' + d[5];
	if(d[6]) t += '<br><b>Status: </b>' + d[6];
	if(d[1]) t += '<br><b>Allocated To: </b>' + d[1];
	if(d[2]) t += '<br><b>Project: </b>' + d[2];
	if(d[3]) t += '<br><b>From: </b>' + date.str_to_user(d[3]);
	if(d[4]) t += '<br><b>To: </b>' + date.str_to_user(d[4]);
	t += '</div>';

	$(this.body).qtip({
		content:t,
		position:{
			corner:{
				tooltip: 'topMiddle', // Use the corner...
				target: 'bottomMiddle' // ...and opposite corner
			}
		},
		style:{
			border: {
				width: 5,
				radius: 10
			},
			padding: 10, 
			tip: true, // Give it a speech bubble tip with automatic corner detection
			name: 'green' // Style it according to the preset 'cream' style
		}
	})

}




