# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.file_manager import get_file_path
import os
from frappe.utils import get_url_to_form, get_link_to_form
import tweepy
from tweepy.error import TweepError
import json

class TwitterSettings(Document):
	def get_authorize_url(self):
		callback_url = "{0}/?cmd=erpnext.crm.doctype.twitter_settings.twitter_settings.callback".format(frappe.utils.get_url())
		auth = tweepy.OAuthHandler(self.consumer_key, self.get_password(fieldname="consumer_secret"), callback_url)
		try:
			redirect_url = auth.get_authorization_url()
			return redirect_url
		except tweepy.TweepError:
			frappe.throw('Error! Failed to get request token.')

	
	def get_access_token(self):
		auth = tweepy.OAuthHandler(self.consumer_key, self.get_password(fieldname="consumer_secret"))
		auth.request_token = { 
			'oauth_token' : self.oauth_token,
			'oauth_token_secret' : self.oauth_verifier 
		}
		try:
			auth.get_access_token(self.oauth_verifier)
			self.db_set("oauth_token", auth.access_token)
			self.db_set("oauth_secret", auth.access_token_secret)
			api = self.get_api()
			user = api.me()
			self.db_set("account_name", user._json["screen_name"])
			self.db_set("profile_pic", user._json["profile_image_url"])
			frappe.local.response["type"] = "redirect"
			location = get_url_to_form("Twitter Settings","Twitter Settings") + "?status=1"
			frappe.local.response["location"] = location
		except:
			frappe.throw('Error! Failed to get access token.')

	def get_api(self):
		# authentication of consumer key and secret 
		auth = tweepy.OAuthHandler(self.consumer_key, self.get_password(fieldname="consumer_secret")) 
		# authentication of access token and secret 
		auth.set_access_token(self.oauth_token, self.get_password(fieldname="oauth_secret")) 

		return tweepy.API(auth)

	def post(self, text, media=None):
		if not media:
			return self.send_tweet(text)

		if media:
			media_id = self.upload_image(media)
			return self.send_tweet(text, media_id)
	
	def upload_image(self, media):
		media = get_file_path(media)

		api = self.get_api()
		media = api.media_upload(media)
		return media.media_id

	def send_tweet(self, text, media_id=None):
		api = self.get_api()
		try:
			if media_id:
				response = api.update_status(status = text, media_ids = [media_id])
				
			else:
				response = api.update_status(status = text)
			return response
			
		except TweepError as e:
			content = json.loads(e.response.content)
			content = content["errors"][0]
			if e.response.status_code == 401:
				frappe.msgprint("{0} With Twitter to Continue".format(get_link_to_form("Twitter Settings","Twitter Settings","Login")))
			frappe.throw(content["message"],title="Twitter Error {0} {1}".format(e.response.status_code, e.response.reason))

@frappe.whitelist()
def callback(oauth_token, oauth_verifier):
	twitter_settings = frappe.get_single("Twitter Settings")
	twitter_settings.db_set("oauth_token", oauth_token)
	twitter_settings.db_set("oauth_verifier", oauth_verifier)
	twitter_settings.get_access_token()
 	frappe.db.commit()
