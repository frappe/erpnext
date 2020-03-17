# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import get_site_url,get_absolute_url
from frappe.model.document import Document
import requests
import json
from frappe.utils.file_manager import get_file, get_file_path
import urllib
from frappe.utils import get_url_to_form, get_link_to_form
class LinkedInSettings(Document):
	def get_authorization_url(self):
		try:
			from urllib.parse import urlencode
		except:
			from urllib import urlencode
		params = urlencode({
			"response_type":"code",
			"client_id": self.consumer_key,
			"redirect_uri": get_site_url(frappe.local.site) + "/?cmd=erpnext.crm.doctype.linkedin_settings.linkedin_settings.callback",
			"scope": "r_liteprofile r_emailaddress w_member_social"
		})

		url = "https://www.linkedin.com/oauth/v2/authorization?{}".format(params)

		return url

	def get_access_token(self, code):
		url = "https://www.linkedin.com/oauth/v2/accessToken"
		try:
			from urllib.parse import urlencode
		except:
			from urllib import urlencode
		body = {
			"grant_type": "authorization_code",
			"code": code,
			"client_id": self.consumer_key,
			"client_secret": self.get_password(fieldname="consumer_secret"),
			"redirect_uri": get_site_url(frappe.local.site) + "/?cmd=erpnext.crm.doctype.linkedin_settings.linkedin_settings.callback",
		}
		headers = {
			"Content-Type": "application/x-www-form-urlencoded"
		}
		
		response = self.http_post(url=url, data=body, headers=headers)
		response = frappe.parse_json(response.content.decode())
		self.db_set("access_token", response["access_token"])

	def get_member_profile(self):
		headers = {
			"Authorization": "Bearer {}".format(self.access_token)
		}
		url = "https://api.linkedin.com/v2/me"
		response = requests.get(url=url, headers=headers)
		response = frappe.parse_json(response.content.decode())
		# self.db_set("person_urn", response["id"],notify=True, commit=True)
		print(response)
		self.db_set("person_urn", response["id"])
		frappe.local.response["type"] = "redirect"
		location = get_url_to_form("LinkedIn Settings","LinkedIn Settings") + "?status=1"
		frappe.local.response["location"] = location

	def post(self, text, media=None):
		if not media:
			return self.post_text(text)
		else:
			media_id = self.upload_image(media)
			if media_id:
				return self.post_text(text, media_id=media_id)
			else:
				frappe.log_error("Failed to upload media.","LinkedIn Upload Error")


	def upload_image(self, media):
		media = get_file_path(media)
		register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"

		body = {
			"registerUploadRequest": {
				"recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
				"owner": "urn:li:person:{0}".format(self.person_urn),
				"serviceRelationships": [{
					"relationshipType": "OWNER",
					"identifier": "urn:li:userGeneratedContent"
				}]
			}
		}
		headers = {
			"Authorization": "Bearer {}".format(self.access_token)
		}
		response = self.http_post(url=register_url, body=body, headers=headers)
		if response.status_code == 200:
			response = response.json()
			asset = response["value"]["asset"]
			upload_url = response["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
			headers['Content-Type']='image/jpeg'
			response = self.http_post(upload_url, headers=headers, data=open(media,"rb"))
			if response.status_code < 200 and response.status_code > 299:
				frappe.throw("Error While Uploading Image", title="{0} {1}".format(response.status_code, response.reason))
				return None
			return asset
		return None


	def post_text(self, text, media_id=None):
		url = "https://api.linkedin.com/v2/ugcPosts"
		headers = {
			"X-Restli-Protocol-Version": "2.0.0",
			"Authorization": "Bearer {}".format(self.access_token),
			"Content-Type": "application/json; charset=UTF-8"
		}
		body = {
			"author": "urn:li:person:{0}".format(self.person_urn),
			"lifecycleState": "PUBLISHED",
			"specificContent": {
				"com.linkedin.ugc.ShareContent": {
					"shareCommentary": {
						"text": text
					},
					"shareMediaCategory": "IMAGE" if media_id else "NONE"
				}
			},
			"visibility": {
				"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
			}
		}
		if media_id:
			body["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [
				{
					"status": "READY",
					"description": {
						"text": ""
					},
					"media": media_id,
					"title": {
						"text":""
					}
				}
			]
		response = self.http_post(url=url, headers=headers, body=body)
		return response

	def http_post(self, url, headers=None, body=None, data=None):
		try:
			response = requests.post(
				url = url,
				json = body,
				data = data,
				headers = headers
			)
			if response.status_code not in [201,200]:
				raise
		except Exception as e:
			content = json.loads(response.content)
			if response.status_code == 401:
				frappe.msgprint("{0} With LinkedIn to Continue".format(get_link_to_form("LinkedIn Settings","LinkedIn Settings","Login")))
 				frappe.throw(content["message"], title="LinkedIn Error - Unauthorized")
			elif response.status_code == 403:
				frappe.msgprint("You Didn't have permission to access this API")
				frappe.throw(content["message"], title="LinkedIn Error - Access Denied")
			else:
				frappe.throw(response.reason, title=response.status_code)

		return response

@frappe.whitelist()
def callback(code=None, error=None, error_description=None):
	if not error:
		linkedin_settings = frappe.get_doc("LinkedIn Settings")
		linkedin_settings.get_access_token(code)
		linkedin_settings.get_member_profile()
		frappe.db.commit()
	else:
		frappe.local.response["message"] = error
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = get_url_to_form("LinkedIn Settings","LinkedIn Settings")