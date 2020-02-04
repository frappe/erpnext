frappe.provide("frappe.patient_history");
frappe.pages['patient_history'].on_page_load = function(wrapper) {
	var me = this;
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Patient History',
		single_column: true
	});

	frappe.breadcrumbs.add("Healthcare");
	let pid = '';
	page.main.html(frappe.render_template("patient_history", {}));
	var patient = frappe.ui.form.make_control({
		parent: page.main.find(".patient"),
		df: {
			fieldtype: "Link",
			options: "Patient",
			fieldname: "patient",
			change: function(){
				if(pid != patient.get_value() && patient.get_value()){
					me.start = 0;
					me.page.main.find(".patient_documents_list").html("");
					get_documents(patient.get_value(), me);
					show_patient_info(patient.get_value(), me);
					show_patient_vital_charts(patient.get_value(), me, "bp", "mmHg", "Blood Pressure");
				}
				pid = patient.get_value();
			}
		},
		only_input: true,
	});
	patient.refresh();

	if (frappe.route_options){
		patient.set_value(frappe.route_options.patient);
	}

	this.page.main.on("click", ".btn-show-chart", function() {
		var	btn_show_id = $(this).attr("data-show-chart-id"), pts = $(this).attr("data-pts");
		var title = $(this).attr("data-title");
		show_patient_vital_charts(patient.get_value(), me, btn_show_id, pts, title);
	});

	this.page.main.on("click", ".btn-more", function() {
		var	doctype = $(this).attr("data-doctype"), docname = $(this).attr("data-docname");
		if(me.page.main.find("."+docname).parent().find('.document-html').attr('data-fetched') == "1"){
			me.page.main.find("."+docname).hide();
			me.page.main.find("."+docname).parent().find('.document-html').show();
		}else{
			if(doctype && docname){
				let exclude = ["patient", "patient_name", 'patient_sex', "encounter_date"];
				frappe.call({
					method: "erpnext.healthcare.utils.render_doc_as_html",
					args:{
						doctype: doctype,
						docname: docname,
						exclude_fields: exclude
					},
					callback: function(r) {
						if (r.message){
							me.page.main.find("."+docname).hide();
							me.page.main.find("."+docname).parent().find('.document-html').html(r.message.html+"\
							<div align='center'><a class='btn octicon octicon-chevron-up btn-default btn-xs\
							btn-less' data-doctype='"+doctype+"' data-docname='"+docname+"'></a></div>");
							me.page.main.find("."+docname).parent().find('.document-html').show();
							me.page.main.find("."+docname).parent().find('.document-html').attr('data-fetched', "1");
						}
					},
					freeze: true
				});
			}
		}
	});

	this.page.main.on("click", ".btn-less", function() {
		var docname = $(this).attr("data-docname");
		me.page.main.find("."+docname).parent().find('.document-id').show();
		me.page.main.find("."+docname).parent().find('.document-html').hide();
	});
	me.start = 0;
	me.page.main.on("click", ".btn-get-records", function(){
		get_documents(patient.get_value(), me);
	});
};

var get_documents = function(patient, me){
	frappe.call({
		"method": "erpnext.healthcare.page.patient_history.patient_history.get_feed",
		args: {
			name: patient,
			start: me.start,
			page_length: 20
		},
		callback: function (r) {
			var data = r.message;
			if(data.length){
				add_to_records(me, data);
			}else{
				me.page.main.find(".patient_documents_list").append("<div class='text-muted' align='center'><br><br>No more records..<br><br></div>");
				me.page.main.find(".btn-get-records").hide();
			}
		}
	});
};

var add_to_records = function(me, data){
	var details = "<ul class='nav nav-pills nav-stacked'>";
	var i;
	for(i=0; i<data.length; i++){
		if(data[i].reference_doctype){
			let label = '';
			if(data[i].subject){
				label += "<br/>"+data[i].subject;
			}
			data[i] = add_date_separator(data[i]);
			if(frappe.user_info(data[i].owner).image){
				data[i].imgsrc = frappe.utils.get_file_link(frappe.user_info(data[i].owner).image);
			}
			else{
				data[i].imgsrc = false;
			}
			var time_line_heading = data[i].practitioner ? `${data[i].practitioner} ` : ``;
			time_line_heading += data[i].reference_doctype + " - "+ data[i].reference_name;
			details += `<li data-toggle='pill' class='patient_doc_menu'
			data-doctype='${data[i].reference_doctype}' data-docname='${data[i].reference_name}'>
			<div class='col-sm-12 d-flex border-bottom py-3'>`;
			if (data[i].imgsrc){
				details += `<span class='mr-3'>
					<img class='avtar' src='${data[i].imgsrc}' width='32' height='32'>
					</img>
			</span>`;
			}else{
				details += `<span class='mr-3 avatar avatar-small' style='width:32px; height:32px;'><div align='center' class='standard-image'
					style='background-color: #fafbfc;'>${data[i].practitioner ? data[i].practitioner.charAt(0) : "U"}</div></span>`;
			}
			details += `<div class='d-flex flex-column width-full'>
					<div>
						`+time_line_heading+` on
							<span>
								${data[i].date_sep}
							</span>
					</div>
					<div class='Box p-3 mt-2'>
						<span class='${data[i].reference_name} document-id'>${label}
							<div align='center'>
								<a class='btn octicon octicon-chevron-down btn-default btn-xs btn-more'
									data-doctype='${data[i].reference_doctype}' data-docname='${data[i].reference_name}'>
								</a>
							</div>
						</span>
						<span class='document-html' hidden  data-fetched="0">
						</span>
					</div>
				</div>
			</div>
			</li>`;
		}
	}
	details += "</ul>";
	me.page.main.find(".patient_documents_list").append(details);
	me.start += data.length;
	if(data.length===20){
		me.page.main.find(".btn-get-records").show();
	}else{
		me.page.main.find(".btn-get-records").hide();
		me.page.main.find(".patient_documents_list").append("<div class='text-muted' align='center'><br><br>No more records..<br><br></div>");
	}
};

var add_date_separator = function(data) {
	var date = frappe.datetime.str_to_obj(data.creation);

	var diff = frappe.datetime.get_day_diff(frappe.datetime.get_today(), frappe.datetime.obj_to_str(date));
	if(diff < 1) {
		var pdate = 'Today';
	} else if(diff < 2) {
		pdate = 'Yesterday';
	} else {
		pdate = frappe.datetime.global_date_format(date);
	}
	data.date_sep = pdate;
	return data;
};

var show_patient_info = function(patient, me){
	frappe.call({
		"method": "erpnext.healthcare.doctype.patient.patient.get_patient_detail",
		args: {
			patient: patient
		},
		callback: function (r) {
			var data = r.message;
			var details = "";
			if(data.image){
				details += "<div><img class='thumbnail' width=75% src='"+data.image+"'></div>";
			}
			details += "<b>" + data.patient_name +"</b><br>" + data.sex;
			if(data.email) details += "<br>" + data.email;
			if(data.mobile) details += "<br>" + data.mobile;
			if(data.occupation) details += "<br><br><b>Occupation :</b> " + data.occupation;
			if(data.blood_group) details += "<br><b>Blood group : </b> " + data.blood_group;
			if(data.allergies) details +=  "<br><br><b>Allergies : </b> "+  data.allergies.replace("\n", "<br>");
			if(data.medication) details +=  "<br><b>Medication : </b> "+  data.medication.replace("\n", "<br>");
			if(data.alcohol_current_use) details +=  "<br><br><b>Alcohol use : </b> "+  data.alcohol_current_use;
			if(data.alcohol_past_use) details +=  "<br><b>Alcohol past use : </b> "+  data.alcohol_past_use;
			if(data.tobacco_current_use) details +=  "<br><b>Tobacco use : </b> "+  data.tobacco_current_use;
			if(data.tobacco_past_use) details +=  "<br><b>Tobacco past use : </b> "+  data.tobacco_past_use;
			if(data.medical_history) details +=  "<br><br><b>Medical history : </b> "+  data.medical_history.replace("\n", "<br>");
			if(data.surgical_history) details +=  "<br><b>Surgical history : </b> "+  data.surgical_history.replace("\n", "<br>");
			if(data.surrounding_factors) details +=  "<br><br><b>Occupational hazards : </b> "+  data.surrounding_factors.replace("\n", "<br>");
			if(data.other_risk_factors) details += "<br><b>Other risk factors : </b> " + data.other_risk_factors.replace("\n", "<br>");
			if(data.patient_details) details += "<br><br><b>More info : </b> " + data.patient_details.replace("\n", "<br>");

			if(details){
				details = "<div style='padding-left:10px; font-size:13px;' align='center'>" + details + "</div>";
			}
			me.page.main.find(".patient_details").html(details);
		}
	});
};

var show_patient_vital_charts = function(patient, me, btn_show_id, pts, title) {
	frappe.call({
		method: "erpnext.healthcare.utils.get_patient_vitals",
		args:{
			patient: patient
		},
		callback: function(r) {
			if (r.message){
				var show_chart_btns_html = "<div style='padding-top:5px;'><a class='btn btn-default btn-xs btn-show-chart' \
				data-show-chart-id='bp' data-pts='mmHg' data-title='Blood Pressure'>Blood Pressure</a>\
				<a class='btn btn-default btn-xs btn-show-chart' data-show-chart-id='pulse_rate' \
				data-pts='per Minutes' data-title='Respiratory/Pulse Rate'>Respiratory/Pulse Rate</a>\
				<a class='btn btn-default btn-xs btn-show-chart' data-show-chart-id='temperature' \
				data-pts='°C or °F' data-title='Temperature'>Temperature</a>\
				<a class='btn btn-default btn-xs btn-show-chart' data-show-chart-id='bmi' \
				data-pts='' data-title='BMI'>BMI</a></div>";
				me.page.main.find(".show_chart_btns").html(show_chart_btns_html);
				var data = r.message;
				let labels = [], datasets = [];
				let bp_systolic = [], bp_diastolic = [], temperature = [];
				let pulse = [], respiratory_rate = [], bmi = [], height = [], weight = [];
				for(var i=0; i<data.length; i++){
					labels.push(data[i].signs_date+"||"+data[i].signs_time);
					if(btn_show_id=="bp"){
						bp_systolic.push(data[i].bp_systolic);
						bp_diastolic.push(data[i].bp_diastolic);
					}
					if(btn_show_id=="temperature"){
						temperature.push(data[i].temperature);
					}
					if(btn_show_id=="pulse_rate"){
						pulse.push(data[i].pulse);
						respiratory_rate.push(data[i].respiratory_rate);
					}
					if(btn_show_id=="bmi"){
						bmi.push(data[i].bmi);
						height.push(data[i].height);
						weight.push(data[i].weight);
					}
				}
				if(btn_show_id=="temperature"){
					datasets.push({name: "Temperature", values: temperature, chartType:'line'});
				}
				if(btn_show_id=="bmi"){
					datasets.push({name: "BMI", values: bmi, chartType:'line'});
					datasets.push({name: "Height", values: height, chartType:'line'});
					datasets.push({name: "Weight", values: weight, chartType:'line'});
				}
				if(btn_show_id=="bp"){
					datasets.push({name: "BP Systolic", values: bp_systolic, chartType:'line'});
					datasets.push({name: "BP Diastolic", values: bp_diastolic, chartType:'line'});
				}
				if(btn_show_id=="pulse_rate"){
					datasets.push({name: "Heart Rate / Pulse", values: pulse, chartType:'line'});
					datasets.push({name: "Respiratory Rate", values: respiratory_rate, chartType:'line'});
				}
				new frappe.Chart( ".patient_vital_charts", {
					data: {
						labels: labels,
						datasets: datasets
					},

					title: title,
					type: 'axis-mixed', // 'axis-mixed', 'bar', 'line', 'pie', 'percentage'
					height: 200,
					colors: ['purple', '#ffa3ef', 'light-blue'],

					tooltipOptions: {
						formatTooltipX: d => (d + '').toUpperCase(),
						formatTooltipY: d => d + ' ' + pts,
					}
				});
			}else{
				me.page.main.find(".patient_vital_charts").html("");
				me.page.main.find(".show_chart_btns").html("");
			}
		}
	});
};
