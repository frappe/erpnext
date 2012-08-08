
/*
 *	erpnext/projects/gantt_task.js
 */
wn.require('js/lib/jQuery.Gantt/css/style.css');wn.require('js/lib/jQuery.Gantt/js/jquery.fn.gantt.min.js');erpnext.show_task_gantt=function(parent,project){$(parent).css('min-height','300px').html('<div class="help-box">Loading...</div>')
var get_source=function(r){var source=[];$.each(r.message,function(i,v){source.push({name:v.project,desc:v.subject,values:[{label:v.subject,desc:v.description||v.subject,from:'/Date("'+v.exp_start_date+'")/',to:'/Date("'+v.exp_end_date+'")/',customClass:{'Open':'ganttRed','Pending Review':'ganttOrange','Working':'','Completed':'ganttGreen','Cancelled':'ganttGray'}[v.status],dataObj:v}]})});return source}
wn.call({method:'projects.page.projects.projects.get_tasks',args:{project:project||''},callback:function(r){$(parent).empty();if(!r.message.length){$(parent).html('<div class="help-box">No Tasks Yet.</div>');}else{var gantt_area=$('<div class="gantt">').appendTo(parent);gantt_area.gantt({source:get_source(r),navigate:project?"button":"scroll",scale:"weeks",minScale:"weeks",maxScale:"months",onItemClick:function(data){wn.set_route('Form','Task',data.name);},onAddClick:function(dt,rowId){newdoc('Task');}});}
$('<button class="btn"><i class="icon icon-plus"></i>\
    Create a new Task</button>').click(function(){wn.model.with_doctype('Task',function(){var new_name=LocalDB.create('Task');if(project)
locals.Task[new_name].project=project;wn.set_route('Form','Task',new_name);});}).appendTo(parent);}})}