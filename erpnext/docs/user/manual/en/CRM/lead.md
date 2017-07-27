To get the customer through the door, you may be doing all or any of the
following:

  * Listing your product on directories.
  * Maintaining an updated and searchable website.
  * Meeting people at trade events.
  * Advertising your product or services.

When you send out the word that you are around and have something valuable to
offer, people will come in to check out your product. These are your Leads.

They are called Leads because they may lead you to a sale. Sales people
usually work on leads by calling them, building a relationship and sending
information about their products or services. It is important to track all
this conversation to enable another person who may have to follow-up on that
contact. The new person is then able to know the history of that particular
Lead.

---

Leads are the  entities constituting a first contact. Leads can be created by a system users or by a web-user. When a lead is created minimal info (name,email) is entered and the lead is (default) linked to the active system user, the owner of the lead  A user configurable drop list is used to classify Status of the lead (Open, Replied etc)

To create a Lead, go to:

> CRM > Lead > New Lead

<img class="screenshot" alt="Lead" src="{{docs_base_url}}/assets/img/crm/lead.png">

ERPNext gives you a lot of options you may want to store about your Leads. For
example what is the source, how likely are they to give you business etc. If
you have a healthy number of leads, this information will help you prioritize
who you want to work with.

> **Tip:** ERPNext makes it easy to follow-up on leads by updating the “Next
Contact” details. This will add a new event in the Calendar for the User who
has to contact the lead next.

### Difference between Lead, Contact and Customer

A Lead is a potential Customer, someone who can give you business. A Customer is an
organization or individual who has given you business before (and has an Account
in your system). A Contact is a person who belongs to the Customer.

A Lead can be converted to a Customer by selecting “Customer” from the **Make**
dropdown. Once the Customer is created, the Lead becomes “Converted” and any
further Opportunities from the same source can be created against this
Customer.

<img class="screenshot" alt="Create Customer" src="{{docs_base_url}}/assets/img/crm/lead-to-customer.gif">

---

### Creation via Portal

If a someone creates an account through the website interface is Lead is automatically created, status is Open and the Owner is the webuser.

After registration the webform Addresses is called, where the web user can enter address information.The address is linked to the lead using the **Lead Name-Address Type** as ID.

If using the Cart functionality, items are ordered the Lead is Converted and a Customer is created using the Web-User Name. Because a Customer can only be linked to a webuser using the (foreign) ID in Contact, such contact has to be created as well.

{next}
