#Outgoing Email Gateway

In the ERPNext, you can customize incoming and Outgoing Email Gateway. On saving an Email Account, ERPNext tries establishing a connection with your email gateway. If your ERPNext account is able to connect fine, then Email Account master is saved. If not, then you might receive an error as indicated below.  

<img alt="Email Setup Error" class="screenshot" src="/docs/assets/img/articles/email-setup-error.png">

This indicates that using login credentials and other email gateway details provided, ERPNext is not able to connect to your email server. Please ensure that you have entered valid email credentials for your Email Gateway. Once you have configured Email Account successfully, you should be able to send and receive emails from your ERPNext account fine.

Note: Your ERPNext account is connected with ERPNext email server by default. If you don't want to use your own email server, you can continue sending emails using an ERPNext email server.