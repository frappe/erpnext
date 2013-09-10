---
{
	"_label": "SMS Setting"
}
---
To integrate SMS in ERPNext, approach a SMS Gateway Provider who prvides HTTP API. They will create an account for you and will provide an unique username and password.

To configure SMS Settings in ERPNext, find out their HTTP API (a document which describes the method of accessing their SMS interface from 3rd party applications). In this document, you will get an URL which is used to send the SMS using HTTP request. Using this URL, you can configure SMS Settings in ERPNext.

Example URL: 
http://instant.smses.com/web2sms.php?username=<USERNAME>&password=<PASSWORD>&to=<
MOBILENUMBER>&sender=<SENDERID>&message=<MESSAGE>


Note: the characters up to the "?" are the SMS Gateway URL

Example:
http://instant.smses.com/web2sms.php?username=abcd&password=abcd&to=9900XXXXXX&sender
=DEMO&message=THIS+IS+A+TEST+SMS
The above url will send sms from account abcd to mobile number 9900XXXXXX with sender ID as 
DEMO with text message as THIS IS A TEST SMS

You can see here some parameters in the URL are static, you will get static values from your SMS Provider like username, password etc. These static values should be entered in Static Parameters table.

![SMS Setting](img/sms-settings1.png)

