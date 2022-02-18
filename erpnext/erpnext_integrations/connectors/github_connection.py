
import frappe
from frappe.data_migration.doctype.data_migration_connector.connectors.base import BaseConnection
from github import Github


class GithubConnection(BaseConnection):
	def __init__(self, connector):
		self.connector = connector

		try:
			password = self.get_password()
		except frappe.AuthenticationError:
			password = None

		if self.connector.username and password:
			self.connection = Github(self.connector.username, self.get_password())
		else:
			self.connection = Github()

		self.name_field = 'id'

	def insert(self, doctype, doc):
		pass

	def update(self, doctype, doc, migration_id):
		pass

	def delete(self, doctype, migration_id):
		pass

	def get(self, remote_objectname, fields=None, filters=None, start=0, page_length=10):
		repo = filters.get('repo')

		if remote_objectname == 'Milestone':
			return self.get_milestones(repo, start, page_length)
		if remote_objectname == 'Issue':
			return self.get_issues(repo, start, page_length)

	def get_milestones(self, repo, start=0, page_length=10):
		_repo = self.connection.get_repo(repo)
		return list(_repo.get_milestones()[start:start+page_length])

	def get_issues(self, repo, start=0, page_length=10):
		_repo = self.connection.get_repo(repo)
		return list(_repo.get_issues()[start:start+page_length])
