# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import requests
from requests_oauthlib import OAuth2
import json
from frappe.utils.file_manager import get_file, get_file_path

class LinkedInSettings(Document):
	def get_authorization_url(self):
		from urllib.parse import urlencode
		params = urlencode({
			"response_type":"code",
			"client_id": self.consumer_key,
			"redirect_uri": "http://crm.erpnext.local:8000/?cmd=erpnext.crm.doctype.linkedin_settings.linkedin_settings.callback",
			"scope": "w_member_social r_liteprofile r_emailaddress"
		},)

		url = "https://www.linkedin.com/oauth/v2/authorization?{}".format(params)

		return url

	def get_access_token(self):
		url = "https://www.linkedin.com/oauth/v2/accessToken"
		from urllib.parse import urlencode
		body = {
			"grant_type": "authorization_code",
			"code": self.oauth_code,
			"client_id": self.consumer_key,
			"client_secret": self.get_password(fieldname="consumer_secret"),
			"redirect_uri": "http://crm.erpnext.local:8000/?cmd=erpnext.crm.doctype.linkedin_settings.linkedin_settings.callback"
		}
		headers = {
			"Content-Type": "application/x-www-form-urlencoded"
		}
		
		try:
			r = requests.post(url, data=body, headers=headers)
			r.raise_for_status()
		except Exception as e:
			print(e)
		res = frappe.parse_json(r.content.decode())
		self.access_token = res["access_token"]
		self.save()
		self.get_me()

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
		r = requests.post(register_url, json=body, headers=headers)
		response = r.json()
		# print(r.headers)
		# print(response)
		# return
		asset = response["value"]["asset"]
		upload_url = response["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]

		r = requests.post(upload_url, headers=headers, files={"file":open(media,"rb")})
		if r.status_code < 200 and r.status_code > 299:
			return None
		return asset

	def get_me(self):
		headers = {
			"Authorization": "Bearer {}".format(self.access_token)
		}
		url = "https://api.linkedin.com/v2/me"
		try:
			r = requests.get(url, headers=headers)
			r.raise_for_status()
		except Exception as e:
			frappe.throw(e)
		response = frappe.parse_json(r.content.decode())
		self.person_urn = response["id"]
		self.save()
		
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/desk#Form/{0}".format(quote("LinkedIn Settings"))

		frappe.msgprint(_("LinkedIn Settings has been configured."))


	def post(self, text, media=None):
		if not media:
			self.post_text(text)
		else:
			media_id = self.upload_image(media)
			if media_id:
				self.post_text(text, media_id=media_id)
			else:
				frappe.msgprint("Image upload to linkedin failed")


	def post_text(self, text, media_id=None):
		url = "https://api.linkedin.com/v2/ugcPosts"
		headers = {
			"X-Restli-Protocol-Version": "2.0.0",
			"Authorization": "Bearer {}".format(self.access_token)
		}
		body = {
			"author": "urn:li:person:{0}".format(self.person_urn),
			"lifecycleState": "PUBLISHED",
			"specificContent": {
				"com.linkedin.ugc.ShareContent":{
					"shareCommentary": {"text":text},
					"shareMediaCategory": "NONE" if not media_id else "IMAGE",
					"media": None if not media_id else [
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
				}
			},
			"visibility": {
				"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
			}
		}
		try:
			r = requests.post(url, json=body, headers=headers)
			r.raise_for_status()
		except Exception as e:
			frappe.throw(e)
		return r

@frappe.whitelist()
def callback(code=None, error=None, error_description=None):
	if not error:
		linkedin_settings = frappe.get_doc("LinkedIn Settings")
		linkedin_settings.oauth_code = code
		linkedin_settings.save()
		linkedin_settings.get_access_token()
		frappe.db.commit()
