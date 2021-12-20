<table class="panel-header" border="0" cellpadding="0" cellspacing="0" width="100%">
	<tr height="10"></tr>
	<tr>
		<td width="15"></td>
		<td>
			<div class="text-medium text-muted">
				<h2>{{_("Exit Interview Scheduled:")}} {{ doc.name }}</h2>
			</div>
		</td>
		<td width="15"></td>
	</tr>
	<tr height="10"></tr>
</table>

<table class="panel-body" border="0" cellpadding="0" cellspacing="0" width="100%">
	<tr height="10"></tr>
	<tr>
		<td width="15"></td>
		<td>
			<div>
				<ul class="list-unstyled" style="line-height: 1.7">
					<li><b>{{_("Employee")}}: </b>{{ doc.employee }} - {{ doc.employee_name }}</li>
					<li><b>{{_("Date")}}: </b>{{ frappe.utils.formatdate(doc.date) }}</li>
					<li><b>{{_("Interviewers")}}:</b> </li>
					{% for entry in doc.interviewers %}
						<ul>
							<li>{{ entry.user }}</li>
						</ul>
					{% endfor %}
					<li><b>{{ _("Interview Document") }}:</b> {{ frappe.utils.get_link_to_form(doc.doctype, doc.name) }}</li>
				</ul>
			</div>
		</td>
		<td width="15"></td>
	</tr>
	<tr height="10"></tr>
</table>
