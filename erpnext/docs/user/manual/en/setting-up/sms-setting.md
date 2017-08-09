# SMS Setting

To integrate SMS in ERPNext, approach a SMS Gateway Provider who provides HTTP
API. They will create an account for you and will provide an unique username
and password.

To configure SMS Settings in ERPNext, find out their HTTP API (a document
which describes the method of accessing their SMS interface from 3rd party
applications). In this document, you will get an URL which is used to send the
SMS using HTTP request. Using this URL, you can configure SMS Settings in
ERPNext.

Example URL:  

    
    
    http://instant.smses.com/web2sms.php?username=<USERNAME>&password;=<PASSWORD>&to;=<MOBILENUMBER>&sender;=<SENDERID>&message;=<MESSAGE>
    

<img class="screenshot" alt="SMS Setting 2" src="/docs/assets/img/setup/sms-settings2.jpg">


> Note: the string up to the "?" is the SMS Gateway URL

Example:

    
    
    http://instant.smses.com/web2sms.php?username=abcd&password;=abcd&to;=9900XXXXXX&sender;
    =DEMO&message;=THIS+IS+A+TEST+SMS

The above URL will send SMS from account abcd to mobile number 9900XXXXXX with
sender ID as DEMO with text message as "THIS IS A TEST SMS"

Note that some parameters in the URL are static.You will get static values
from your SMS Provider like username, password etc. These static values should
be entered in the Static Parameters table.

<img class="screenshot" alt="SMS Setting" src="/docs/assets/img/setup/sms-settings1.png">

{next}
