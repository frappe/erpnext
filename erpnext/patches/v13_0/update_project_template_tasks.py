# Copyright (c) 2019, Frappe and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

def execute():
    frappe.reload_doc("projects", "doctype", "project_template")
    frappe.reload_doc("projects", "doctype", "project_template_task")
    frappe.reload_doc("projects", "doctype", "project_template")
    for template_name in frappe.db.sql(""" 
        select 
            name 
        from 
            `tabProject Template` """, 
        as_dict=1):
       
        template = frappe.get_doc("Project Template", template_name.name)
        replace_tasks = False
        new_tasks = []
        for task in template.tasks:
            if task.subject:
                replace_tasks = True
                new_task = frappe.get_doc(dict(
                    doctype = "Task",
                    subject = task.subject,
                    start = task.start,
                    duration = task.duration,
                    task_weight = task.task_weight,
                    description = task.description,
                    is_template = 1
                )).insert()
                new_tasks.append(new_task.name)
        if replace_tasks:
            template.tasks = []
            for tsk in new_tasks:
                template.append("tasks", {
                    "task": tsk
                })  
            template.save()