# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Article(Document):
	def get_article(self):
		pass

@frappe.whitelist()
def get_topics_without_article(article):
	data = []
	for entry in frappe.db.get_all('Topic'):
		topic = frappe.get_doc('Topic', entry.name)
		topic_contents = [tc.content for tc in topic.topic_content]
		if not topic_contents or article not in topic_contents:
			data.append(topic.name)
	return data