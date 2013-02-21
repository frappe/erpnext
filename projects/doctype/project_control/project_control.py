# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes

from webnotes.utils import add_days, cint, cstr, date_diff, flt, now, nowdate, add_days
from webnotes.model import db_exists
from webnotes.model.bean import copy_doclist
from webnotes import msgprint
from webnotes.utils.email_lib import sendmail
sql = webnotes.conn.sql
	


class DocType:
	def __init__(self,d,dl):		
		self.doc, self.doclist = d,dl
	
	def get_projects(self, arg):
	# project list
		pl=[]
		status={}
		if arg == 'Open':
			pl = [p[0] for p in sql("select name from `tabProject` where status = 'Open' order by creation desc limit 20")]
			for p1 in pl:
				status[p1] = 'Open'
		elif arg == 'Completed':
			pl = [p[0] for p in sql("select name from `tabProject` where status = 'Completed' order by creation desc limit 20")]
			for p2 in pl:
				status[p2] = 'Completed'
		elif arg == 'Cancelled':
			pl = [p[0] for p in sql("select name from `tabProject` where status = 'Cancelled' order by creation desc limit 20")]
			for p3 in pl:
				status[p3] = 'Cancelled'
		else:
			#pl = [p[0] for p in sql("select name from `tabProject` order by creation desc limit 20")]
			pl1 = sql("select name, status from `tabProject` order by creation desc limit 20", as_dict=1)
			for p4 in pl1:
				status[p4['name']] = p4['status']
				pl.append(p4['name'])
		
		# milestones in the next 7 days for active projects
		ml = webnotes.conn.convert_to_lists(sql("select t1.milestone_date, t1.milestone, t1.parent from `tabProject Milestone` t1, tabProject t2 where t1.parent = t2.name and t2.status='Open' and DATEDIFF(t1.milestone_date, CURDATE()) BETWEEN 0 AND 7 ORDER BY t1.milestone_date ASC"))

		# percent of activity completed per project
		comp = {}
		n_tasks = {}
		
		for p in pl:
			t1 = sql('select count(*) from tabTask where project=%s and docstatus!=2', p)[0][0]
			n_tasks[p] = t1 or 0
			if t1:
				t2 = sql('select count(*) from tabTask where project=%s and docstatus!=2 and status="Closed"', p)[0][0]
				comp[p] = cint(flt(t2)*100/t1)
		
		return {'pl':pl, 'ml':ml, 'comp':comp, 'n_tasks':n_tasks, 'status':status}
		
	def get_resources(self):
		ret = {}

		# resource list
		rl = sql("select distinct allocated_to, assignee_email from tabTask")

		# get open & closed tickets
		for r in rl:
			if r[0]:
				ret[r[1]] = {}
				ret[r[1]]['id'] = r[0]
				ret[r[1]]['Total'] = sql("select count(*) from tabTask where allocated_to=%s and docstatus!=2", r[0])[0][0]
				ret[r[1]]['Closed'] = sql("select count(*) from tabTask where allocated_to=%s and status='Closed' and docstatus!=2", r[0])[0][0]
				ret[r[1]]['percent'] = cint(flt(ret[r[1]]['Closed']) * 100 / ret[r[1]]['Total'])

		return ret

	# --------------------------------------------------------------
	# for Gantt Chart

	def get_init_data(self, arg=''):
		pl = [p[0] for p in sql('select name from tabProject where docstatus != 2')]
		rl = [p[0] for p in sql('select distinct allocated_to from tabTask where docstatus != 2 and ifnull(allocated_to,"") != ""')]
		return {'pl':pl, 'rl':rl}

	def get_tasks(self, arg):
		start_date, end_date, project, resource = arg.split('~~~')

		cl = ''
		if project and project != 'All':
			cl = " and ifnull(project,'') = '%s'" % project

		if resource and resource != 'All':
			cl = " and ifnull(allocated_to,'') = '%s'" % resource

		tl = sql("""
			select subject, allocated_to, project, exp_start_date, exp_end_date, priority, status, name
			from tabTask 
			where 
				((exp_start_date between '%(st)s' and '%(end)s') or 
				(exp_end_date between '%(st)s' and '%(end)s') or 
				(exp_start_date < '%(st)s' and exp_end_date > '%(end)s')) %(cond)s order by exp_start_date limit 100""" % {'st': start_date, 'end': end_date, 'cond':cl})

		return webnotes.conn.convert_to_lists(tl)
	
	def declare_proj_completed(self, arg):
		chk = sql("select name from `tabTask` where project=%s and status='Open'", arg)
		if chk:
			chk_lst = [x[0] for x in chk]
			msgprint("Task(s) "+','.join(chk_lst)+" has staus 'Open'. Please submit all tasks against this project before closing the project.")
			return cstr('false')
		else:
			sql("update `tabProject` set status = 'Completed' where name = %s", arg)
			return cstr('true')
			
			
def sent_reminder_task():
	task_list = sql("""
		select subject, allocated_to, project, exp_start_date, exp_end_date,
			priority, status, name, senders_name, opening_date, review_date, description 
		from tabTask
		where task_email_notify=1 
			and sent_reminder=0 
			and status='Open' 
			and exp_start_date is not null""",as_dict=1)
	for i in task_list:		
		if date_diff(i['exp_start_date'],nowdate()) ==2:
			msg2="""<h2>Two days to complete: %(name)s</h2>
			<p>This is a reminder for the task %(name)s has been assigned to you 
				by %(senders_name)s on %(opening_date)s</p>
			<p><b>Subject:</b> %(subject)s </p>
			<p><b>Project:</b> %(project)s</p>
			<p><b>Expected Start Date:</b> %(exp_start_date)s</p>
			<p><b>Expected End Date:</b> %(exp_end_date)s</p>
			<p><b>Review Date:</b> %(review_date)s</p>
			<p><b>Details:</b> %(description)s</p>
			<p>If you have already completed this task, please update the system</p>
			<p>Good Luck!</p>
			<p>(This notification is autogenerated)</p>""" % i
			sendmail(i['allocated_to'], msg=msg2, subject='A task has been assigned')
			sql("update `tabTask` set sent_reminder='1' where name='%(name)s' and allocated_to= '%(allocated_to)s'" % i)	
	
