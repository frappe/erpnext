from __future__ import unicode_literals
import frappe
import requests, base64
from xml.etree import ElementTree
from frappe import _
from frappe.utils import cint, flt, get_bench_path, get_datetime
class BankAPI:
    pass

@frappe.whitelist()
def encrypt_credential(api):
    doc = frappe.get_doc("API Detail", str(api))
    url = doc.api_link
    user_id = password = ""
    for a in doc.item:
        if a.param == "user_id":
            user_id = a.defined_value
        elif a.param == "password":
            password = a.defined_value
    header_string = str(user_id)+":"+str(password)
    header_bytes = header_string.encode("utf-8")
    return header_bytes, url

@frappe.whitelist()
def intra_payment(from_acc, trans_amount, promo_no, to_acc, unique_transaction_no):
    if not frappe.db.get_value('Bank Payment Settings', "BOBL", 'enable_one_to_one'):
        return
    '''
    doc = frappe.get_doc("API Detail", "ONE TO ONE - INTRA BANK")
    url = doc.api_link
    for a in doc.item:
        if a.param == "user_id":
            user_id = a.defined_value
        elif a.param == "password":
            password = a.defined_value
    '''
    header_credential, url = encrypt_credential(api="ONE TO ONE - INTRA BANK")

    payload="""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:v1="http://BaNCS.TCS.com/webservice/TransferDepositAccountFundSecuredInterface/v1" xmlns:ban="http://TCS.BANCS.Adapter/BANCSSchema">			
        <soapenv:Header/>			
        <soapenv:Body>			
            <v1:transferDepositAccountFundSecured>			
                <DepAcctFundXferRq>			
                    <ban:RqHeader>			
                    <!--Optional:-->			
                    <ban:Filler1></ban:Filler1>			
                    <!--Optional:-->			
                    <ban:MsgLen></ban:MsgLen>			
                    <!--Optional:-->			
                    <ban:Filler2></ban:Filler2>			
                    <!--Optional:-->			
                    <ban:MsgTyp></ban:MsgTyp>			
                    <!--Optional:-->			
                    <ban:Filler3></ban:Filler3>			
                    <!--Optional:-->			
                    <ban:CycNum></ban:CycNum>			
                    <!--Optional:-->			
                    <ban:MsgNum></ban:MsgNum>			
                    <!--Optional:-->			
                    <ban:SegNum></ban:SegNum>			
                    <!--Optional:-->			
                    <ban:SegNum2></ban:SegNum2>			
                    <!--Optional:-->			
                    <ban:FrontEndNum></ban:FrontEndNum>			
                    <!--Optional:-->			
                    <ban:TermlNum></ban:TermlNum>			
                    <!--Optional:-->			
                        <ban:InstNum>003</ban:InstNum>			
                    <ban:BrchNum>00010</ban:BrchNum>			
                    <!--Optional:-->			
                    <ban:WorkstationNum></ban:WorkstationNum>			
                    <!--Optional:-->			
                    <ban:TellerNum>8885</ban:TellerNum>			
                    <!--Optional:-->			
                    <ban:TranNum></ban:TranNum>			
                    <!--Optional:-->			
                    <ban:JrnlNum></ban:JrnlNum>			
                    <!--Optional:-->			
                    <ban:HdrDt></ban:HdrDt>			
                    <!--Optional:-->			
                    <ban:Filler4></ban:Filler4>			
                    <!--Optional:-->			
                    <ban:Filler5></ban:Filler5>			
                    <!--Optional:-->			
                    <ban:Filler6></ban:Filler6>			
                    <!--Optional:-->			
                    <ban:Flag1></ban:Flag1>			
                    <!--Optional:-->			
                    <ban:Flag2></ban:Flag2>			
                    <!--Optional:-->			
                    <ban:Flag3></ban:Flag3>			
                    <!--Optional:-->			
                    <ban:Flag4>W</ban:Flag4>			
                    <ban:Flag5>Y</ban:Flag5>			
                    <!--Optional:-->			
                    <ban:Flag6></ban:Flag6>			
                    <!--Optional:-->			
                    <ban:Flag7></ban:Flag7>			
                    <!--Optional:-->			
                    <ban:SprvsrID></ban:SprvsrID>			
                    <!--Optional:-->			
                    <ban:SupDate></ban:SupDate>			
                    <!--Optional:-->			
                    <ban:CheckerID1></ban:CheckerID1>			
                    <!--Optional:-->			
                    <ban:ParentBlinkJrnlNum></ban:ParentBlinkJrnlNum>			
                    <!--Optional:-->			
                    <ban:CheckerID2></ban:CheckerID2>			
                    <!--Optional:-->			
                    <ban:BlinkJrnlNum></ban:BlinkJrnlNum>			
                    <ban:UUIDSource></ban:UUIDSource>			
                    <ban:UUIDNUM></ban:UUIDNUM>			
                    <!--Optional:-->			
                    <ban:UUIDSeqNo></ban:UUIDSeqNo>			
                    </ban:RqHeader>			
                    <ban:Data>			
                    <ban:FrmAcctNum>{0}</ban:FrmAcctNum>			
                    <ban:Amt>{1}</ban:Amt>			
                    <ban:PromoNum>{2}</ban:PromoNum>			
                    <ban:ToAcctNum>{3}</ban:ToAcctNum>
                            
                    <!--Optional:-->			
                    <ban:TrnAmt>{1}</ban:TrnAmt>			
                            
                    <!--Optional:-->			
                    <ban:StmtNarr>{4}</ban:StmtNarr>			
                            
                    </ban:Data>			
                </DepAcctFundXferRq>			
            </v1:transferDepositAccountFundSecured>			
        </soapenv:Body>			
        </soapenv:Envelope>""".format(from_acc, trans_amount, promo_no, to_acc, unique_transaction_no)
    '''
    headers = {
    'Authorization': 'Basic %s' % base64.b64encode(header_credential),
    'Content-Type': 'application/xml'
    }
    '''
    headers = {
    'Authorization': 'Basic RVBBWVRUUDpwYXNzd29yZDEyMyQ=',
    'Content-Type': 'application/xml'
    }
    
    response = requests.request("POST", url, headers=headers, data=payload)
    
    namespaces = {
        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        'ns2': 'http://TCS.BANCS.Adapter/BANCSSchema',
        'ns3': 'http://BaNCS.TCS.com/webservice/TransferDepositAccountFundSecuredInterface/v1'
    }

    JrnlNum=""
    errorMessage=""
    successMessage= ""
    message = ""
    status = ""
    dom = ElementTree.fromstring(response.text)
    for name in dom.findall('./soap:Body/ns3:transferDepositAccountFundSecuredResponse/DepAcctFundXferRs/ns2:RsHeader/ns2:JrnlNum', namespaces):
        JrnlNum = name.text
    for name in dom.findall('./soap:Body/ns3:transferDepositAccountFundSecuredResponse/DepAcctFundXferRs/ns2:Stat/ns2:ErrorMessage/ns2:ErrorMessage', namespaces):
        errorMessage = name.text
    for name in dom.findall('./soap:Body/ns3:transferDepositAccountFundSecuredResponse/DepAcctFundXferRs/ns2:Stat/ns2:OkMessage/ns2:RcptData', namespaces):
        successMessage = name.text 
    if successMessage:
        message = successMessage
        status = "Success"
    else:
        message = errorMessage
        status = "Failed"

    return {"jrnl_no":JrnlNum, "status":status, "message":message}

@frappe.whitelist()
def inter_payment(Amt, PayeeAcctNum, BnfcryAcct, BnfcryName, BnfcryAcctTyp, BnfcryRmrk, RemitterName, BfscCode, RemitterAcctType, PEMSRefNum):
    if not frappe.db.get_value('Bank Payment Settings', "BOBL", 'enable_one_to_one'):
        return
    '''
    doc = frappe.get_doc("API Detail", "ONE TO ONE - INTER BANK")
    url = doc.api_link
    for a in doc.item:
        if a.param == "user_id":
            user_id = a.defined_value
        elif a.param == "password":
            password = a.defined_value
    '''
    header_credential, url = encrypt_credential(api="ONE TO ONE - INTER BANK")

    if Amt > 1000000:
        ModeOfPmt = str("01")
    else:
        ModeOfPmt = str("02")   
    #url = "http://10.30.30.195:8888/OutwardDebit/OutwardDebitInterfaceHttpService"
    payload="""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:v1="http://BaNCS.TCS.com/webservice/OutwardDebitInterface/v1" xmlns:ban="http://TCS.BANCS.Adapter/BANCSSchema">
            <soapenv:Header/>
            <soapenv:Body>
                <v1:outwardDebit>
                    <OutwardDrRq>
                        <ban:RqHeader>
                        <!--Optional:-->
                        <ban:Filler1></ban:Filler1>
                        <!--Optional:-->
                        <ban:MsgLen></ban:MsgLen>
                        <!--Optional:-->
                        <ban:Filler2></ban:Filler2>
                        <!--Optional:-->
                        <ban:MsgTyp></ban:MsgTyp>
                        <!--Optional:-->
                        <ban:Filler3></ban:Filler3>
                        <!--Optional:-->
                        <ban:CycNum></ban:CycNum>
                        <!--Optional:-->
                        <ban:MsgNum></ban:MsgNum>
                        <!--Optional:-->
                        <ban:SegNum></ban:SegNum>
                        <!--Optional:-->
                        <ban:SegNum2></ban:SegNum2>
                        <!--Optional:-->
                        <ban:FrontEndNum></ban:FrontEndNum>
                        <!--Optional:-->
                        <ban:TermlNum></ban:TermlNum>
                        <!--Optional:-->
                        <ban:InstNum>003</ban:InstNum>
                        <ban:BrchNum>00010</ban:BrchNum>
                        <!--Optional:-->
                        <ban:WorkstationNum></ban:WorkstationNum>
                        <!--Optional:-->
                        <ban:TellerNum>8885</ban:TellerNum>
                        <!--Optional:-->
                        <ban:TranNum></ban:TranNum>
                        <!--Optional:-->
                        <ban:JrnlNum></ban:JrnlNum>
                        <!--Optional:-->
                        <ban:HdrDt></ban:HdrDt>
                        <!--Optional:-->
                        <ban:Filler4></ban:Filler4>
                        <!--Optional:-->
                        <ban:Filler5></ban:Filler5>
                        <!--Optional:-->
                        <ban:Filler6></ban:Filler6>
                        <!--Optional:-->
                        <ban:Flag1></ban:Flag1>
                        <!--Optional:-->
                        <ban:Flag2></ban:Flag2>
                        <!--Optional:-->
                        <ban:Flag3></ban:Flag3>
                        <!--Optional:-->
                        <ban:Flag4>W</ban:Flag4>
                        <ban:Flag5>Y</ban:Flag5>
                        <!--Optional:-->
                        <ban:Flag6></ban:Flag6>
                        <!--Optional:-->
                        <ban:Flag7></ban:Flag7>
                        <!--Optional:-->
                        <ban:SprvsrID></ban:SprvsrID>
                        <!--Optional:-->
                        <ban:SupDate></ban:SupDate>
                        <!--Optional:-->
                        <ban:CheckerID1></ban:CheckerID1>
                        <!--Optional:-->
                        <ban:ParentBlinkJrnlNum></ban:ParentBlinkJrnlNum>
                        <!--Optional:-->
                        <ban:CheckerID2></ban:CheckerID2>
                        <!--Optional:-->
                        <ban:BlinkJrnlNum></ban:BlinkJrnlNum>
                        <ban:UUIDSource></ban:UUIDSource>
                        <ban:UUIDNUM></ban:UUIDNUM>
                        <!--Optional:-->
                        <ban:UUIDSeqNo></ban:UUIDSeqNo>
                        </ban:RqHeader>
                        <ban:Data>
                        <ban:ModeOfPmt>{0}</ban:ModeOfPmt>
                        <ban:Amt>{1}</ban:Amt>
                        <ban:PayeeAcctNum>{2}</ban:PayeeAcctNum>
                        <ban:BnfcryAcct>{3}</ban:BnfcryAcct>
                        <ban:BnfcryName>{4}</ban:BnfcryName>
                        <ban:BnfcryAcctTyp>{5}</ban:BnfcryAcctTyp>
                        <!--Optional:-->
                        <ban:BnfcryRmrk>{6}</ban:BnfcryRmrk>
                        <!--Optional:-->
                        <ban:RemitterRmrk>{6}</ban:RemitterRmrk>
                        <ban:RemitterName>{7}</ban:RemitterName>
                        <ban:BfscCode>{8}</ban:BfscCode>
                        <ban:BnfcryAmt>{1}</ban:BnfcryAmt>
                        <ban:RemitterAcctTyp>{9}</ban:RemitterAcctTyp>
                        <ban:SndToRcvrInfo>{6}</ban:SndToRcvrInfo>
                        <!--Optional:-->
                        <ban:SndToRcvrInfo1></ban:SndToRcvrInfo1>
                        <!--Optional:-->
                        <ban:SndToRcvrInfo2></ban:SndToRcvrInfo2>
                        <ban:Comsn>0</ban:Comsn>
                        <ban:TtlAmt>{1}</ban:TtlAmt>
                        <ban:TxnCurrCode1>BTN</ban:TxnCurrCode1>
                        <!--Optional:-->
                        <ban:Amount3></ban:Amount3>
                        <!--Optional:-->
                        <ban:EmailID></ban:EmailID>
                        <ban:RemitterAcctNum>{2}</ban:RemitterAcctNum>
                        <ban:PEMSRefNum>{10}</ban:PEMSRefNum>
                        </ban:Data>
                    </OutwardDrRq>
                </v1:outwardDebit>
            </soapenv:Body>
        </soapenv:Envelope>""".format(ModeOfPmt, Amt, PayeeAcctNum, BnfcryAcct, BnfcryName, BnfcryAcctTyp, BnfcryRmrk, RemitterName, BfscCode, RemitterAcctType, PEMSRefNum)
    headers = {
    'Authorization': 'Basic RVBBWVRUUDpwYXNzd29yZDEyMyQ=',
    'Content-Type': 'application/xml'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    from xml.etree import ElementTree

    namespaces = {
        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        'ns2': 'http://TCS.BANCS.Adapter/BANCSSchema',
        'ns3': 'http://BaNCS.TCS.com/webservice/OutwardDebitInterface/v1'
    }

    JrnlNum=""
    errorMessage=""
    successMessage= ""
    dom = ElementTree.fromstring(response.text)
    for name in dom.findall('./soap:Body/ns3:outwardDebitResponse/OutwardDrRs/ns2:RsHeader/ns2:JrnlNum', namespaces):
        JrnlNum = name.text
    for name in dom.findall('./soap:Body/ns3:outwardDebitResponse/OutwardDrRs/ns2:Stat/ns2:ErrorMessage/ns2:ErrorMessage', namespaces):
        errorMessage = name.text
    for name in dom.findall('./soap:Body/ns3:outwardDebitResponse/OutwardDrRs/ns2:Stat/ns2:OkMessage/ns2:RcptData', namespaces):
        successMessage = name.text

    if successMessage:
        message = successMessage
        status = "Success"
    else:
        message = errorMessage
        status = "Failed"

    return {"jrnl_no":JrnlNum, "status":status, "message":message}

@frappe.whitelist()
def inr_remittance(AcctNum, Amt, BnfcryAcct, BnfcryName, BnfcryAddr1, IFSC, BankCode, PurpCode, RemittersName, RemittersAddr1, ComsnOpt, PromoCode, PemsRefNum):
    if not frappe.db.get_value('Bank Payment Settings', "BOBL", 'enable_one_to_one'):
        return
    
    header_credential, url = encrypt_credential(api="ONE TO ONE - INR Remmittance")
    '''
    doc = frappe.get_doc("API Detail", "ONE TO ONE - INR Remmittance")
    url = doc.api_link
    for a in doc.item:
        if a.param == "user_id":
            user_id = a.defined_value
        elif a.param == "password":
            password = a.defined_value
    '''
    #url = "http://10.30.30.195:8088/INRRemittanceByTransferSecured/INRRemittanceByTransferSecuredInterfaceHttpService"
    payload = """
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
    xmlns:v1="http://BaNCS.TCS.com/webservice/INRRemittanceByTransferSecuredInterface/v1" 
    xmlns:ban="http://TCS.BANCS.Adapter/BANCSSchema">
    <soapenv:Header/>
    <soapenv:Body>
        <v1:iNRRemittanceByTransferSecured>
            <INRRemittanceByXferRq>
                <ban:RqHeader>
                <!--Optional:-->
                <ban:Filler1></ban:Filler1>
                <!--Optional:-->
                <ban:MsgLen></ban:MsgLen>
                <!--Optional:-->
                <ban:Filler2></ban:Filler2>
                <!--Optional:-->
                <ban:MsgTyp></ban:MsgTyp>
                <!--Optional:-->
                <ban:Filler3></ban:Filler3>
                <!--Optional:-->
                <ban:CycNum></ban:CycNum>
                <!--Optional:-->
                <ban:MsgNum></ban:MsgNum>
                <!--Optional:-->
                <ban:SegNum></ban:SegNum>
                <!--Optional:-->
                <ban:SegNum2></ban:SegNum2>
                <!--Optional:-->
                <ban:FrontEndNum></ban:FrontEndNum>
                <!--Optional:-->
                <ban:TermlNum></ban:TermlNum>
                <!--Optional:-->
                    <ban:InstNum>03</ban:InstNum>
                <ban:BrchNum>00010</ban:BrchNum>
                <!--Optional:-->
                <ban:WorkstationNum></ban:WorkstationNum>
                <!--Optional:-->
                <ban:TellerNum>8882</ban:TellerNum>
                <!--Optional:-->
                <ban:TranNum></ban:TranNum>
                <!--Optional:-->
                <ban:JrnlNum></ban:JrnlNum>
                <!--Optional:-->
                <ban:HdrDt></ban:HdrDt>
                <!--Optional:-->
                <ban:Filler4></ban:Filler4>
                <!--Optional:-->
                <ban:Filler5></ban:Filler5>
                <!--Optional:-->
                <ban:Filler6></ban:Filler6>
                <!--Optional:-->
                <ban:Flag1></ban:Flag1>
                <!--Optional:-->
                <ban:Flag2></ban:Flag2>
                <!--Optional:-->
                <ban:Flag3></ban:Flag3>
                <!--Optional:-->
                <ban:Flag4>W</ban:Flag4>
                <ban:Flag5>Y</ban:Flag5>
                <!--Optional:-->
                <ban:Flag6></ban:Flag6>
                <!--Optional:-->
                <ban:Flag7></ban:Flag7>
                <!--Optional:-->
                <ban:SprvsrID></ban:SprvsrID>
                <!--Optional:-->
                <ban:SupDate></ban:SupDate>
                <!--Optional:-->
                <ban:CheckerID1></ban:CheckerID1>
                <!--Optional:-->
                <ban:ParentBlinkJrnlNum></ban:ParentBlinkJrnlNum>
                <!--Optional:-->
                <ban:CheckerID2></ban:CheckerID2>
                <!--Optional:-->
                <ban:BlinkJrnlNum></ban:BlinkJrnlNum>
                <ban:UUIDSource></ban:UUIDSource>
                <ban:UUIDNUM></ban:UUIDNUM>
                <!--Optional:-->
                <ban:UUIDSeqNo></ban:UUIDSeqNo>
                </ban:RqHeader>
            <ban:Data>
                <ban:AcctNum>{0}</ban:AcctNum>
                <!--Optional:-->
                <ban:CustName></ban:CustName>
                <!--Optional:-->
                <ban:Bal></ban:Bal>
                <!--Optional:-->
                <ban:ModeOfPay></ban:ModeOfPay>
                <ban:Amt>{1}</ban:Amt>
                <!--Optional:-->
                <ban:AmtCur></ban:AmtCur>
                <!--Optional:-->
                <ban:Comsn>2</ban:Comsn>
                <!--Optional:-->
                <ban:TtlAmt></ban:TtlAmt>
                <!--Optional:-->
                <ban:TtlAmtCur>BTN</ban:TtlAmtCur>
                <ban:BnfcryAcct>{2}</ban:BnfcryAcct>
                <ban:BnfcryName>{3}</ban:BnfcryName>
                <ban:BnfcryAddr1>{4}</ban:BnfcryAddr1>
                <!--Optional:-->
                <ban:BnfcryAddr2></ban:BnfcryAddr2>
                <!--Optional:-->
                <ban:BnfcryAddr3></ban:BnfcryAddr3>
                <ban:IFSC>{5}</ban:IFSC>
                <ban:BankCode>{6}</ban:BankCode>
                <ban:PurpCode>{7}</ban:PurpCode>
                <ban:RemittersName>{8}</ban:RemittersName>
                <ban:RemittersAddr1>{9}</ban:RemittersAddr1>
                <!--Optional:-->
                <ban:RemittersAddr2></ban:RemittersAddr2>
                <!-- Optional:-->
                <ban:RemittersAddr3></ban:RemittersAddr3>
                <ban:MailIdMobile></ban:MailIdMobile>
                <!--Optional:-->
                <ban:ComsnOpt>{10}</ban:ComsnOpt>
                <!--Optional:-->
                <ban:PromoCode>{11}</ban:PromoCode>
                <!--Optional:-->
                <ban:PemsRefNum>{12}</ban:PemsRefNum>
                </ban:Data>
            </INRRemittanceByXferRq>
        </v1:iNRRemittanceByTransferSecured>
    </soapenv:Body>""".format(AcctNum, Amt, BnfcryAcct, BnfcryName, BnfcryAddr1, IFSC, BankCode, PurpCode, RemittersName, RemittersAddr1, ComsnOpt, PromoCode, PemsRefNum)

    headers = {
    'Authorization': 'Basic RVBBWVRUUDpwYXNzd29yZDEyMyQ=',
    'Content-Type': 'application/xml'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    namespaces = {
        'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
        'ns2': 'http://TCS.BANCS.Adapter/BANCSSchema',
        'ns3': 'http://BaNCS.TCS.com/webservice/INRRemittanceByTransferSecuredInterface/v1'
    }

    JrnlNum=""
    errorMessage=""
    successMessage= ""
    dom = ElementTree.fromstring(response.text)
    for name in dom.findall('./soap:Body/ns3:iNRRemittanceByTransferSecuredResponse/INRRemittanceByXferRs/ns2:RsHeader/ns2:JrnlNum', namespaces):
        JrnlNum = name.text
    for name in dom.findall('./soap:Body/ns3:iNRRemittanceByTransferSecuredResponse/INRRemittanceByXferRs/ns2:Stat/ns2:ErrorMessage/ns2:ErrorMessage', namespaces):
        errorMessage = name.text
    for name in dom.findall('./soap:Body/ns3:iNRRemittanceByTransferSecuredResponse/INRRemittanceByXferRs/ns2:Stat/ns2:OkMessage/ns2:RcptData', namespaces):
        successMessage = name.text

    if successMessage:
        message = successMessage
        status = "Success"
    else:
        message = errorMessage
        status = "Failed"

    return {"jrnl_no":JrnlNum, "status":status, "message":message}
    
@frappe.whitelist()
def fetch_balance(account_no):
    if not account_no:
        return {"message":"Please provide account no"}
    if not frappe.db.get_value('Bank Payment Settings', "BOBL", 'enable_one_to_one'):
        return
    header_credential, url = encrypt_credential(api="BOB Customer Balance Enquiry")
    '''
    doc = frappe.get_doc("API Detail", "BOB Customer Balance Enquiry")
    url = doc.api_link
    for a in doc.item:
        if a.param == "user_id":
            user_id = a.defined_value
        elif a.param == "password":
            password = a.defined_value
    '''

    #url = "http://10.30.30.195:8088/EnquireShort/EnquireShortInterfaceHttpService"
    payload="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:v1="http://BaNCS.TCS.com/webservice/EnquireShortInterface/v1" xmlns:ban="http://TCS.BANCS.Adapter/BANCSSchema">
                <soapenv:Header/>
                <soapenv:Body>
                    <v1:enquireShort>
                        <ShrtInqRq>
                            <ban:RqHeader>
                            <!--Optional:-->
                            <ban:Filler1></ban:Filler1>
                            <!--Optional:-->
                            <ban:MsgLen></ban:MsgLen>
                            <!--Optional:-->
                            <ban:Filler2></ban:Filler2>
                            <!--Optional:-->
                            <ban:MsgTyp></ban:MsgTyp>
                            <!--Optional:-->
                            <ban:Filler3></ban:Filler3>
                            <!--Optional:-->
                            <ban:CycNum></ban:CycNum>
                            <!--Optional:-->
                            <ban:MsgNum></ban:MsgNum>
                            <!--Optional:-->
                            <ban:SegNum></ban:SegNum>
                            <!--Optional:-->
                            <ban:SegNum2></ban:SegNum2>
                            <!--Optional:-->
                            <ban:FrontEndNum></ban:FrontEndNum>
                            <!--Optional:-->
                            <ban:TermlNum></ban:TermlNum>
                            <!--Optional:-->
                            <ban:InstNum>003</ban:InstNum>
                            <ban:BrchNum>00010</ban:BrchNum>
                            <!--Optional:-->
                            <ban:WorkstationNum></ban:WorkstationNum>
                            <!--Optional:-->
                            <ban:TellerNum>8885</ban:TellerNum>
                            <!--Optional:-->
                            <ban:TranNum></ban:TranNum>
                            <!--Optional:-->
                            <ban:JrnlNum></ban:JrnlNum>
                            <!--Optional:-->
                            <ban:HdrDt></ban:HdrDt>
                            <!--Optional:-->
                            <ban:Filler4></ban:Filler4>
                            <!--Optional:-->
                            <ban:Filler5></ban:Filler5>
                            <!--Optional:-->
                            <ban:Filler6></ban:Filler6>
                            <!--Optional:-->
                            <ban:Flag1></ban:Flag1>
                            <!--Optional:-->
                            <ban:Flag2></ban:Flag2>
                            <!--Optional:-->
                            <ban:Flag3></ban:Flag3>
                            <!--Optional:-->
                            <ban:Flag4>W</ban:Flag4>
                            <ban:Flag5>Y</ban:Flag5>
                            <!--Optional:-->
                            <ban:Flag6></ban:Flag6>
                            <!--Optional:-->
                            <ban:Flag7></ban:Flag7>
                            <!--Optional:-->
                            <ban:SprvsrID></ban:SprvsrID>
                            <!--Optional:-->
                            <ban:SupDate></ban:SupDate>
                            <!--Optional:-->
                            <ban:CheckerID1></ban:CheckerID1>
                            <!--Optional:-->
                            <ban:ParentBlinkJrnlNum></ban:ParentBlinkJrnlNum>
                            <!--Optional:-->
                            <ban:CheckerID2></ban:CheckerID2>
                            <!--Optional:-->
                            <ban:BlinkJrnlNum></ban:BlinkJrnlNum>
                            <ban:UUIDSource></ban:UUIDSource>
                            <ban:UUIDNUM></ban:UUIDNUM>
                            <!--Optional:-->
                            <ban:UUIDSeqNo></ban:UUIDSeqNo>
                            </ban:RqHeader>
                            <ban:Data>
                            <ban:AcctNum>{}</ban:AcctNum>
                            </ban:Data>
                        </ShrtInqRq>
                    </v1:enquireShort>
                </soapenv:Body>
                </soapenv:Envelope>""".format(account_no)

    headers = {
    'Authorization': 'Basic RVBBWVRUUDpwYXNzd29yZDEyMyQ=',
    'Content-Type': 'application/xml'
    }

    try:
        response = requests.request("POST", url, headers=headers, data=payload, timeout=5)
        from xml.etree import ElementTree
        namespaces = {
            'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
            'ns2': 'http://TCS.BANCS.Adapter/BANCSSchema',
            'ns3': 'http://BaNCS.TCS.com/webservice/EnquireShortInterface/v1'
        }

        dom = ElementTree.fromstring(response.text)

        for name in dom.findall('./soap:Body/ns3:enquireShortResponse/ShrtInqRs/ns2:ShrtInqData/ns2:AcctName', namespaces):
            account_holder = name.text

        for name in dom.findall('./soap:Body/ns3:enquireShortResponse/ShrtInqRs/ns2:ShrtInqData/ns2:AvailBal', namespaces):
            avail_bal = name.text

        balance_amt = avail_bal.replace(" CR","")
        return {'status':'0','account_holder':account_holder, "balance_amount":balance_amt, "message": "Success"}
    except requests.exceptions.RequestException as err:
        return {'status':'1', 'message':'Respomnse time out', 'error': err}
