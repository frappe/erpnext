# Patient

In ERPNext Healthcare, the Patient document corresponds any individual who is the recipient of healthcare services you provide. For every ERPNext Healthcare document, it is important to have a Patient associated with it. You can create a new Patient from
> Healthcare > Masters > Patient > New Patient

<img class="screenshot" alt="ERPNext Healthcare" src="/docs/assets/img/healthcare/patient_1.png">

The Patient document holds most details that are required to identify and qualify a patient. You can enter as much information available while creating the Patient. All information in the patient document is presented on the Consultation screen for easy lookup and you can always update this information. Other data like observations, vital signs etc. are not part of the Patient document. These could be recorded during patient encounters and will be available as part of the Patient Medical Record.

<img class="screenshot" alt="ERPNext Healthcare" src="/docs/assets/img/healthcare/patient_2.png">

### Patient as a Customer

ERPNext Accounts makes use of "Customer" document for booking all transactions. So, you may want to associate every Patient to be associated with a Customer in ERPNext. By default, ERPNext Healthcare creates a Customer alongside a Patient and links to it - every transaction against a Patient is booked against the associated Customer. If, for some reason you do not intend to use the ERPNext Accounts module you can turn this behavior off by unchecking this flag
>Healthcare > Setup > Healthcare Settings > Manage Customer

In many cases, you may want to associate multiple Patients to a single Customer against whom you want to book the transactions. For instance, a Veterinarian would require the care services provided to different pets of an individual invoiced against a single Customer.

<img class="screenshot" alt="ERPNext Healthcare" src="/docs/assets/img/healthcare/patient_3.png">

The Patient Relation section of the Patient allows you to select how a Patient is related to another Patient in the system. This is optional, but will be quite handy if you want to use ERPNext in a fertility clinic, for example.

### Registration Fee
Many clinical facilities collect a registration fee during Registration. You can turn this feature on and set the registration fee amount by checking this flag
> Healthcare > Setup > Healthcare Settings > Collect Fee for Patient Registration

If you have this enabled, all new Patients you create will by default be in Disabled mode and will be enabled only after Invoicing the Registration Fee. To create Invoice and record the payment receipt, you can use the "Invoice Patient Registration" button in the Patient document.

> Note: For all ERPNext Healthcare documents, "Disabled" Patients are filtered out.

### Grant access to Patient Portal
ERPNext Healthcare allows you to create a portal user associated with a Patient by simply entering the user email id. A welcome email will be sent to the Patient email address to "Complete" registration.

### Actions
From the Patient document, the following links are enabled

* Vital Signs: "Create > Vital Signs" button will take you to the new Vital Signs screen to record the vitals of the Patient.

* View Patient Medical Record.

* Consultation: You can directly create a new Consultation to record the details of patient encounter.

> Note: User should have privileges (User Role) to view the buttons
