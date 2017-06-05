// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

cur_frm.add_fetch("student", "title", "student_name");

frappe.ui.form.on('Report Card', {
	refresh: function(frm) {

	}
});

frappe.ui.form.on("Report Card", {
	onload: function(frm){
		if (frm.doc.student){
			frm.events.student(frm);
		}
		cur_frm.set_query("academic_term",function(){
			return{
				"filters":{
					"academic_year": (frm.doc.academic_year)
				}
			};
		});
	},
	student: function(frm){
		frappe.call({
			method: "erpnext.schools.api.getstudentsresultinfo",
			args: {
				"student": frm.doc.student
			},
			callback: function(r) {
				console.log(r.message)
				if (r.message){
					frm.events.test_event(frm, r.message);
				}
			}
		});
	},
	test_event: function(frm, results){

		var $table_c = $('<table>'),
			$table_h = $('<thead>'),
			$table_b = $('<tbody>'),
			$table_r = $('<tr>'),
			table_headers = [['Course'],[]],
			json_var = [],
			results = results;

		for(var a=0; a<results[0].score_breakdown.length; a++){
			console.log("First For Loop");
			table_headers[0].push(results[0].score_breakdown[a].criteria);
			table_headers[1].push(results[0].score_breakdown[a].maximum_score);
		}

		table_headers[0].push.apply(table_headers[0],['Total Score','Grade']);
		table_headers[1].push(results[0].maximum_score);
		console.log(table_headers);

		for(var i=0; i<table_headers[0].length; i++){
			console.log("Second For Loop");
			if(['Course','Grade'].indexOf(table_headers[0][i]) > -1){
				$table_r.append(($('<th>').prop('rowspan','2')).text(table_headers[0][i]));
			} else {
				$table_r.append($('<th>').text(table_headers[0][i]));
			}
		}

		$table_h.append($table_r);

		var $table_r2 = $('<tr>');

		if(table_headers[1].length > 0){
			for(var l=0; l<table_headers[1].length; l++){
				$table_r2.append($('<th>').text("Max="+table_headers[1][l]));
			}
		}

		$table_h.append($table_r2);


		for(var j=0; j<results.length; j++){
			console.log("Third For Loop");
			var $table_row = $('<tr>');
			$table_row.append($('<td>').html(results[j].course));

			for(var k=0; k<results[j].score_breakdown.length; k++){
				$table_row.append($('<td>').text(results[j].score_breakdown[k].score));
				console.log("This for loop (k) is called" + (k+1) + 'times')
			}
			$table_row.append($('<td>').text(results[j].score));
			$table_row.append($('<td>').text(results[j].grade));
			$table_b.append($table_row);
			console.log("This for loop (j) is called" + (j+1) + 'times')
		}

		$table_c.prop('class','table table-bordered');
		$table_c.append($table_h);
		$table_c.append($table_b);
		console.log($table_c)
		json_var.push(table_headers);
		json_var.push(results);
		frm.set_value("white_elephant",JSON.stringify(json_var));
		$(frm.fields_dict.results.wrapper).html($table_c);
	}
});