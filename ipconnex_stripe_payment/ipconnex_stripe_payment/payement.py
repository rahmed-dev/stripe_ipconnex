
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
import json
from six import string_types
import stripe
import time
import random
from datetime import datetime, timezone
import calendar

def setup_install():
    try:
        email_templates= frappe.get_all(
                             "Email Template",
                            filters={"name": "Stripe Notification IPCONNEX Default template" },
                            fields=["name"])
        if(len(email_templates)==0):
            email_template_doc= frappe.get_doc(
                {   "doctype": "Email Template",
                    "__newname": "Stripe Notification IPCONNEX Default template",
                    "subject": "Payment Notification - Notification de Payment ",
                    "use_html": 0,
                    "response": "<div class=\"ql-editor read-mode\"><h1>Payment Notification - Notification de Payment</h1><h3><br></h3><p><span style=\"color: rgb(0, 0, 0);\">Dear </span>{{ customer }}</p><p><br></p><p>We are pleased to inform you that your payment for<span style=\"color: rgb(0, 0, 0);\"> </span><strong style=\"color: rgb(0, 0, 0);\"> {{ doctype }} : # {{ name }}</strong><span style=\"color: rgb(0, 0, 0);\">&nbsp;</span> has been successfully processed <span style=\"color: rgb(0, 0, 0);\">!</span></p><p><br></p><p><span style=\"color: rgb(0, 0, 0);\">The paid amount is :&nbsp;</span><strong style=\"color: rgb(0, 0, 0);\">$ {{ amount }}&nbsp;</strong>for a total amount of : <span style=\"color: rgb(0, 0, 0);\">&nbsp;</span><strong style=\"color: rgb(0, 0, 0);\">$ {{ grand_total }} </strong></p><p><br></p><p>Payment Reference : <strong style=\"color: rgb(0, 0, 0);\">{{ stripe_payment_ref }} </strong></p><p><span style=\"color: rgb(0, 0, 0);\">﻿Last Card Digits : ****</span><strong style=\"color: rgb(0, 0, 0);\"> {{ card_last_digits }} </strong></p><p><br></p><p>If you have any questions or need further assistance, <span style=\"color: rgb(0, 0, 0);\">free to contact us for more information.</span></p><p><br></p><p><span style=\"color: rgb(0, 0, 0);\">Kind Regards,</span></p><p>_________________________________________________________________</p><p><br></p><p>Cher {{ customer }},</p><p><br></p><p>Nous sommes heureux de vous informer que votre paiement pour <strong style=\"color: rgb(0, 0, 0);\">{{ doctype }} : # {{ name }}</strong><span style=\"color: rgb(0, 0, 0);\"> </span>a été traité avec succès !</p><p><br></p><p>Le montant payé est de :<span style=\"color: rgb(0, 0, 0);\">&nbsp;</span><strong style=\"color: rgb(0, 0, 0);\">$ {{ amount }}</strong> pour un montant total de : <span style=\"color: rgb(0, 0, 0);\">&nbsp;</span><strong style=\"color: rgb(0, 0, 0);\">$ {{ grand_total }} </strong></p><p><br></p><p>Référence de paiement : <strong style=\"color: rgb(0, 0, 0);\">{{ stripe_payment_ref }} </strong></p><p>Derniers chiffres de la carte : <strong style=\"color: rgb(0, 0, 0);\">**** {{ card_last_digits }} </strong></p><p><br></p><p>Si vous avez des questions ou avez besoin de plus d'assistance, n'hésitez pas à nous contacter pour plus d'informations.</p><p><br></p><p>Cordialement,</p></div>"
                          })
            email_template_doc.save(ignore_permissions=True)
    except:
        """fail to create template"""   

    # Add Auto Process Field to sales Invoice
    doctype = "Sales Invoice"
    field_name = "process_on_submit"
    field_type="Check"
    meta=frappe.get_meta(doctype)
    existing_fields=[field.fieldname for field in frappe.get_meta(doctype).fields ]

    """
    if field_name not in existing_fields and False:
        field_doc=frappe.get_doc({
                'parent': doctype, 
                'parentfield': 'fields', 
                'parenttype': 'DocType', 
                'fieldname': field_name, 
                'label': 'Process On Submit', 
                'fieldtype': field_type,  
                'doctype': 'DocField'
        })
        field_doc.insert(ignore_permissions = True)
    """

    # Create link
    links_list=frappe.get_all(
                                "DocType Link",
                                filters={"link_doctype": "Stripe Customer","parent":"Customer" },
                                fields=["name"])
    if( len(links_list)==0):
        link_doc=frappe.get_doc({
            "parent":"Customer",
            "parentfield":"links",
            "parenttype":"Doctype",
            "link_doctype":"Stripe Customer",
            "link_fieldname":"customer",
            "group":"Payments",
            "doctype":"DocType Link"
        })
        link_doc.insert(ignore_permissions = True)

@frappe.whitelist(allow_guest=True) 
def generateClientSecret(amount,currency,methods,description=""):
    cmd=frappe.local.request.form.to_dict().get('cmd', '')
    if cmd.startswith('ipconnex_stripe_payment.ipconnex_stripe_payment.payement'):
        frappe.throw(_("This function is not allowed for Guest users"), frappe.PermissionError)
    currency='cad'
    methods=['card']
    try:
        stripe_settings=frappe.db.get_all("Stripe Settings",fields=["publishable_key","secret_key"],order_by='is_default desc,modified desc', limit_page_length=1)
        if(len(stripe_settings)==0):
            return{
                "error":'Set Stripe Settings first !',
                "status":0
            }
        stripe.api_key=stripe_settings[0].secret_key
        payment_intent = stripe.PaymentIntent.create(
            amount=amount,  
            currency=currency,
            payment_method_types=methods,
            description=description
        )
        return {
            "client_secret":payment_intent.client_secret,
            "status":1
        }
    except stripe.error.StripeError as e:
        return {
            "error":str(e),
            "status":0
        }
    

@frappe.whitelist(allow_guest=True) 
def checkPaymentStatus(client_secret):
    cmd=frappe.local.request.form.to_dict().get('cmd', '')
    if cmd.startswith('ipconnex_stripe_payment.ipconnex_stripe_payment.payement'):
        frappe.throw(_("This function is not allowed for Guest users"), frappe.PermissionError)
    try:     
        stripe_settings=frappe.db.get_all("Stripe Settings",fields=["publishable_key","secret_key"],order_by='is_default desc,modified desc', limit_page_length=1)
        if(len(stripe_settings)==0):
            return{
                "error":'Set Stripe Settings first !',
                "status":0
            }
        stripe.api_key=stripe_settings[0].secret_key
        payment_intent = stripe.PaymentIntent.retrieve(client_secret.split("_secret_")[0])
        #print(f"PaymentIntent status: {payment_intent.status}")
 
        if payment_intent.status == "succeeded":
            return {
                "title":"Success",
                "description":""+payment_intent.description,
                "message":"payment has been successfully processed.",
                "status":1
            }
        elif payment_intent.status == "requires_payment_method":
            return {
                "title":"Info",
                "description":"",
                "message":"Waiting for your payment ",
                "status":1
            }
        else:
            return {
                "title":"Error",
                "description":"",
                "message":"Transaction failed ! server error ",
                "status":1
            }

    except stripe.error.StripeError as e:
        return {
            "error":str(e),
            "status":0
        }

@frappe.whitelist(allow_guest=True) 
def getCustomer(email, full_name,stripe_acc=""):
    # you can allow guest by creating server script only but they dont have a direct access to it
    cmd=frappe.local.request.form.to_dict().get('cmd', '')
    if cmd.startswith('ipconnex_stripe_payment.ipconnex_stripe_payment.payement'):
        frappe.throw(_("This function is not allowed for Guest users"), frappe.PermissionError)
    # Continue 
    try:
        if(stripe_acc)    :
            stripe_settings=frappe.db.get_all("Stripe Settings",fields=["secret_key"],order_by='is_default desc,modified desc',filters={"name":stripe_acc}, limit_page_length=1)
            if(len(stripe_settings)==0):
                return {"message":f"Stripe Setting {stripe_acc} not found ","status":0}
            stripe.api_key = stripe_settings[0]["secret_key"]
        else :        
            stripe_settings=frappe.db.get_all("Stripe Settings",fields=["secret_key"],order_by='is_default desc,modified desc', limit_page_length=1)
            if(len(stripe_settings)==0):
                return {"message":"Please configure Stripe Settings first","status":0}
            stripe.api_key = stripe_settings[0]["secret_key"]
        customers = stripe.Customer.list(email=email).auto_paging_iter()
        for customer in customers:
            if customer.name == full_name:
                return {"id":customer.id,"message":"The Stripe Customer already exists ","status":1}
        new_customer = stripe.Customer.create(email=email, name=full_name)
        return  {"id":new_customer.id,"message":"A New Stripe Customer Created","status":1}
    except Exception as e :
        return  {"message":str(e),"status":0}
    
@frappe.whitelist(allow_guest=True) 
def getCustomerCards(customer_email):
    # you can allow guest by creating server script only but they dont have a direct access to it
    cmd=frappe.local.request.form.to_dict().get('cmd', '')
    if cmd.startswith('ipconnex_stripe_payment.ipconnex_stripe_payment.payement'):
        frappe.throw(_("This function is not allowed for Guest users"), frappe.PermissionError)
    try:
        stripe_customers=frappe.db.get_all("Stripe Customer",
                    filters={"email":customer_email},
                    fields=["name","email","card_token","stripe_id","stripe_account"],order_by='modified desc', limit_page_length=1)
        if(len(stripe_customers)==0): 
            return {"message":"Customer Card token unfound","status":0}
        stripe_settings=frappe.db.get_all("Stripe Settings",fields=["name","secret_key"],order_by='is_default desc,modified desc', limit_page_length=0)
        if(len(stripe_settings)==0):
            return {"message":"Please configure Stripe Settings first","status":0}
        
        card_details = []
        for stripe_setting in stripe_settings:    
            cards_part=get_cards_by_email(stripe_setting["secret_key"],stripe_setting["name"], stripe_customers[0]["email"])
            card_details.extend(cards_part)

        card_details = sorted(card_details, key=lambda x: x['created'],reverse=True)
        return {"result":card_details,"status":1,"message":"Cards Updated !"}
    except Exception as e :
        return {"message":str(e),"status":0 ,"result":card_details}

    
@frappe.whitelist() 
def processPayment(doctype,docname):
    try:
        invoice_doc=frappe.get_doc(doctype,docname)
        stripe_customers= frappe.get_all(
            "Stripe Customer",
            filters={"customer":invoice_doc.customer},
            order_by='modified desc',
            fields=["name"])
        if(len(stripe_customers)!=0 and len(invoice_doc.customer)!=0 )    :
            stripe_customer=frappe.get_doc("Stripe Customer",stripe_customers[0].name)
            filters={}
            if(stripe_customer.stripe_account):
                filters={"name":stripe_customer.stripe_account}
            stripe_settings=frappe.db.get_all("Stripe Settings",fields=["secret_key","pay_to","email_template","email_sending_account"],filters=filters,order_by='is_default desc,modified desc', limit_page_length=1)
            if(len(stripe_settings)==0):
                return {"message":"Please configure Stripe Settings first","status":0}
            #stripe.api_key = stripe_settings[0]["secret_key"]
            pay_to = stripe_settings[0]["pay_to"]
            sender=stripe_settings[0]["email_sending_account"]
            email_template=stripe_settings[0]["email_template"]
            if( len(stripe_customer.cards_list)==0):
                return {"message":"No cards found ! please add a payment method to the current customer","status":0}
            dateStr = frappe.utils.nowdate() 
            for stripe_card in stripe_customer.cards_list:
                try:            
                    doc_status=frappe.db.get_value(doctype,docname,"status")
                    if doc_status not in ["Partly Paid", "Unpaid", "Overdue"] :
                        return 
                    payment_method_id=stripe_card.card_id
                    if(invoice_doc.disable_rounded_total):
                        amount=min(invoice_doc.outstanding_amount,invoice_doc.grand_total)
                    else:
                        amount=invoice_doc.outstanding_amount
                    amount_cent=int(amount*100)
                    #use new card item
                    stripe_doc=frappe.get_doc("Stripe Settings",stripe_card.stripe_account )
                    pay_to = stripe_doc.pay_to
                    sender= stripe_doc.email_sending_account
                    email_template=stripe_doc.email_template
                    stripe.api_key = stripe_doc.secret_key
                    payment_intent = stripe.PaymentIntent.create(
                        customer=stripe_card.stripe_id,  
                        payment_method=payment_method_id, 
                        amount=amount_cent,  
                        currency=invoice_doc.currency.lower(),  
                        description=doctype+"#"+docname,
                        confirm=True,  
                        automatic_payment_methods={
                            "enabled": True,
                            "allow_redirects": "never"
                        }
                    )
                    result= {"message":"Invoice Payed using Stripe #"+payment_intent.id,"status":1}
                    try : 
                        payment_entry = frappe.get_doc({
                            "doctype": "Payment Entry",
                            'party_type': 'Customer',
                            'party': invoice_doc.customer,
                            'paid_amount': amount,
                            'received_amount': amount,
                            'target_exchange_rate': 1.0,
                            "paid_from": invoice_doc.debit_to,
                            'paid_to_account_currency': invoice_doc.currency,
                            "paid_from_account_currency": invoice_doc.currency,
                            'paid_to': pay_to,
                            "reference_no": "**** "+stripe_card.last_digits+"/stripe:"+payment_intent.id,
                            "reference_date": dateStr,
                            'company': invoice_doc.company,
                            'mode_of_payment': 'Credit Card',
                            "status": "Submitted",
                            "docstatus": 1,
                            "references": [
                                {
                                    "reference_doctype": invoice_doc.doctype,
                                    "reference_name": invoice_doc.name,
                                    "total_amount": invoice_doc.grand_total,
                                    "allocated_amount":amount,
                                    "exchange_rate": 1.0,
                                    "exchange_gain_loss": 0.0,
                                    "parentfield": "references",
                                    "parenttype": "Payment Entry",
                                    "doctype": "Payment Entry Reference",
                                },
                            ],
                        })
                        payment_entry.save(ignore_permissions=True)  
                        if(email_template and sender ):
                            email_sender= frappe.db.get_value('Email Account', sender ,'email_id')
                            template_doc=frappe.get_doc("Email Template",email_template)
                            mail_template=template_doc.response
                            mail_subject=template_doc.subject
                            context={"amount":amount,
                                    "customer":invoice_doc.customer,
                                    "customer_name":invoice_doc.customer_name,
                                    "grand_total":invoice_doc.grand_total,
                                    "doctype":invoice_doc.doctype,
                                    "name":invoice_doc.name,
                                    "card_last_digits":stripe_card.last_digits,
                                    "stripe_payment_ref":payment_intent.id,
                                    "exp_card":stripe_card.last_digits
                                    }
                            mail_content =frappe.render_template(mail_template,context=context )
                            mail_subject =frappe.render_template(mail_subject,context=context )
                            frappe.sendmail(
                                    recipients=stripe_customer.email,
                                    sender=email_sender,
                                    subject=mail_subject,
                                    content=mail_content,     
                                    doctype=invoice_doc.doctype,
                                    name=invoice_doc.name,
                                    read_receipt= "0",
                                    print_letterhead= "1",
                                    now=True
                                    #now=True
                            )
                            frappe.get_doc({
                                "doctype": "Communication",
                                "communication_type": "Communication",
                                "content": mail_content,
                                "subject": mail_subject,
                                "sent_or_received": "Sent",
                                "recipients": stripe_customer.email,
                                "sender": email_sender,
                                "reference_doctype": invoice_doc.doctype,
                                "reference_name": invoice_doc.name,
                            }).insert(ignore_permissions=True)
                        frappe.db.commit()   
                    except e : 
                        result["_exception"]="Exception : "+str(e)
                    return result
                except: 
                    payment_method_id=""
            return {"message":"Failed to process payment please check customer cards ","status":0}
        else :
            return {"message":"No Customer Found  ! please link the current Invoice's Customer to Stripe ","status":0}
    except Exception as e :
        return {"message":str(e),"status":0}
    
@frappe.whitelist(allow_guest=True)
def getNewCardToken(customer_id,stripe_acc=""):
    # you can allow guest by creating server script only but they dont have a direct access to it
    cmd=frappe.local.request.form.to_dict().get('cmd', '')
    if cmd.startswith('ipconnex_stripe_payment.ipconnex_stripe_payment.payement'):
        frappe.throw(_("This function is not allowed for Guest users"), frappe.PermissionError)
    try:        
        filters={}
        if(stripe_acc):
            filters={"name":stripe_acc}
        stripe_settings=frappe.db.get_all("Stripe Settings",fields=["secret_key","pay_to","email_template","email_sending_account"],filters=filters,order_by='is_default desc,modified desc', limit_page_length=1)
        if(len(stripe_settings)==0):
            return {"message":"Please configure Stripe Settings first","status":0}
        stripe.api_key = stripe_settings[0]["secret_key"]
        setup_intent = stripe.SetupIntent.create(
            customer=customer_id,
            payment_method_types=['card']
        )
        return {"result":setup_intent.client_secret,"status":1,"message":"Cards Token Updated !"}
    except stripe.error.StripeError as e:
        return {"message":str(e),"status":0}


@frappe.whitelist()
def getEmail(customer):
    user_roles = frappe.get_all("Has Role", filters={"parent": frappe.session.user}, fields=["role"])
    user_roles = [role.role for role in user_roles]
    is_admin = "System Manager" in user_roles or "Accounts Manager" in user_roles
    # you can allow guest by creating server script only but they dont have a direct access to it
    cmd=frappe.local.request.form.to_dict().get('cmd', '')

    if cmd.startswith('ipconnex_stripe_payment.ipconnex_stripe_payment.payement') and not is_admin:
        frappe.throw(_("This function is not allowed for Guest users"), frappe.PermissionError) 
        
    try:    
        contacts_name = frappe.db.get_all("Dynamic Link",fields=["parent"],filters={"link_doctype": "Customer","link_name": customer,
                "parenttype": "Contact"},
                order_by='modified', limit_page_length=0)
        emails=[]
        for contact in contacts_name:
            email_doc=frappe.get_doc("Contact", contact.parent)
            email=email_doc.email_id
            if email not in emails and email_doc.is_primary_contact  == 1  : 
                emails.append(email)
        return {"result":",".join(emails),"status":1}
    except stripe.error.StripeError as e:
        return {"message":str(e),"status":0}
    



def get_cards_by_email(api_key, account_name, customer_email):
    """Fetch all cards associated with an email in a specific Stripe account."""
    stripe.api_key = api_key
    cards = []

    # Search for customers by email
    customers = stripe.Customer.list(email=customer_email)

    for customer in customers.auto_paging_iter():
        # List payment methods for the customer
        payment_methods = stripe.PaymentMethod.list(
            customer=customer['id'],
            type='card'
        )
        for payment_method in payment_methods.auto_paging_iter():
            cards.append({
                "card_id" : payment_method['id'],
                "brand":payment_method['card']['brand'].upper(),
                "exp_date":  str(payment_method["card"]["exp_month"])+"/"+str(payment_method["card"]["exp_year"]),
                "last_digits" : payment_method['card']['last4'],
                "created":datetime.fromtimestamp(payment_method['created'], tz=timezone.utc).strftime('%Y-%m-%d'),
                "stripe_id" :customer['id'] ,
                "stripe_account" : account_name
            })
        
        #Clean old cards 
        setup_intents = stripe.SetupIntent.list(customer=customer['id'])
        for setup_intent in setup_intents.auto_paging_iter():
            if(setup_intent['status'] == 'requires_payment_method' ):
                try:
                    stripe.SetupIntent.cancel(setup_intent['id'])
                except stripe.error.StripeError as e:
                    msg=f"Failed to cancel SetupIntent {setup_intent['id']}: {e.user_message}"
    return cards

@frappe.whitelist()
def updateCards(client_token):
    try:
        stripe_customers=frappe.db.get_all("Stripe Customer",
                    filters={"card_token":client_token },
                    fields=["name","email","card_token","stripe_id","stripe_account"],order_by='modified desc', limit_page_length=1)
        if(len(stripe_customers)==0): 
            return {"message":"Customer Card token unfound","status":0}
        stripe_settings=frappe.db.get_all("Stripe Settings",fields=["name","secret_key"],order_by='is_default desc,modified desc', limit_page_length=0)
        if(len(stripe_settings)==0):
            return {"message":"Please configure Stripe Settings first","status":0}
        
        card_details = []
        for stripe_setting in stripe_settings:    
            cards_part=get_cards_by_email(stripe_setting["secret_key"],stripe_setting["name"], stripe_customers[0]["email"])
            card_details.extend(cards_part)

        card_details = sorted(card_details, key=lambda x: x['created'],reverse=True)

        stripe_customer=frappe.get_doc("Stripe Customer",stripe_customers[0].name)

        stripe_customer.set("cards_list", card_details) 
        stripe_customer.card_token=""
        stripe_customer.save(ignore_permissions=True)
        try :
            filters={}
            if(stripe_customers[0]["stripe_account"]):
                filters={"name":stripe_customers[0]["stripe_account"]}
            stripe_settings=frappe.db.get_all("Stripe Settings",fields=["secret_key"],filters=filters,order_by='is_default desc,modified desc', limit_page_length=1)
            stripe.api_key = stripe_settings[0]["secret_key"]
            setup_intent = stripe.SetupIntent.create(
                customer=stripe_customer.stripe_id,
                payment_method_types=['card']
            )
            stripe_customer.card_token=setup_intent.client_secret
            stripe_customer.save(ignore_permissions=True)
        except Exception as e:
             {"status":1,"message":"Cards Updated !","notif":"Card not updated ... "+ str(e)}

        return {"status":1,"message":"Cards Updated !"}
    except Exception as e :
        return {"message":"Please contact the website Administrator"+str(e),"status":0}


@frappe.whitelist()
def deleteCard(client_name,card_id,card_idx):
    try:
        card_idx=int(card_idx)
        has_access=len(frappe.get_list(doctype="Stripe Customer",filters={"name":client_name}, limit_page_length=0))==1
        if( has_access ):
            stripe_customers=frappe.db.get_all("Stripe Customer",
                        filters={"name":client_name},
                        fields=["name","email","card_token","stripe_id","stripe_account"],order_by='modified desc', limit_page_length=1)
            if(len(stripe_customers)==0): 
                return {"message":"Customer Card token unfound","status":0}
            
            stripe_customer=frappe.get_doc("Stripe Customer",stripe_customers[0].name)
            if card_idx < len(stripe_customer.cards_list):
                if stripe_customer.cards_list[card_idx].card_id==card_id:        
                    stripe_settings=frappe.db.get_all("Stripe Settings",fields=["secret_key","pay_to","email_template","email_sending_account"],filters={"name":stripe_customer.cards_list[card_idx].stripe_account},order_by='is_default desc,modified desc', limit_page_length=1)
                    if(len(stripe_settings)==0):
                        return {"message":"Server error ! Please contact the website Administrator ","status":0}
                    stripe.api_key = stripe_settings[0]["secret_key"]
                    payment_methods = stripe.PaymentMethod.list(
                        customer=stripe_customer.cards_list[card_idx].stripe_id,
                        type="card"
                    )
                    if payment_methods['data']:
                        stripe.PaymentMethod.detach(stripe_customer.cards_list[card_idx].card_id)
                        stripe_customer=frappe.get_doc("Stripe Customer",stripe_customers[0].name)
                        card_details = stripe_customer.get("cards_list")
                        del card_details[card_idx]
                        stripe_customer.set("cards_list", card_details) 
                        stripe_customer.save(ignore_permissions=True)
                        return {"message":f"{stripe_customer.cards_list[card_idx].brand} Card **** {stripe_customer.cards_list[card_idx].last_digits} removed from the account","status":1}
                    else:
                        return {"message":"Please contact the website Administrator","status":0}
                else: 
                    return {"message":"Please contact the website Administrator","status":0}
        else :            
            return {"message":"You don't have access to this document ","status":0}
    except Exception as e :
        return {"message":"Please contact the website Administrator "+str(e),"status":0}




def checkProcessInvoice(doc, method):
    if doc.status not in ["Partly Paid", "Unpaid", "Overdue"] :
        return 
    doc_status=frappe.db.get_value(doc.doctype,doc.name,"status")
    if doc_status not in ["Partly Paid", "Unpaid", "Overdue"] :
        return 
    try:
        stripe_customers= frappe.db.get_all("Stripe Customer",fields=["name","auto_process","process_delay","stripe_account"],filters={"customer":doc.customer},order_by='modified desc', limit_page_length=0)
        filters={}
        if(stripe_customers[0]["stripe_account"]):
            filters={"name":stripe_customers[0]["stripe_account"]}
        stripe_settings=frappe.db.get_all("Stripe Settings",fields=["secret_key","pay_to","email_template","email_sending_account"],filters=filters,order_by='is_default desc,modified desc', limit_page_length=1)
        if(len(stripe_settings)==0):
            return {"message":"Please configure Stripe Settings first","status":0}
        stripe.api_key = stripe_settings[0]["secret_key"]
        pay_to = stripe_settings[0]["pay_to"]
        sender=stripe_settings[0]["email_sending_account"]
        email_template=stripe_settings[0]["email_template"]


        if( (len(stripe_customers)!=0 and len(doc.customer)!=0 ) and ( stripe_customers[0].auto_process and stripe_customers[0].process_delay==0)  )   :
            stripe_customer=frappe.get_doc("Stripe Customer",stripe_customers[0].name)
            customer_id=stripe_customer.stripe_id
            if( len(stripe_customer.cards_list)==0):
                frappe.msgprint("Error : No cards found ! please add a payment method to the current customer")
                return
            dateStr = frappe.utils.nowdate() 
            for stripe_card in stripe_customer.cards_list :
                try:
                    doc_status=frappe.db.get_value(doc.doctype,doc.name,"status")
                    if doc_status not in ["Partly Paid", "Unpaid", "Overdue"] :
                        return 
                    payment_method_id=stripe_card.card_id
                    if(doc.disable_rounded_total):
                        amount=min(doc.outstanding_amount,doc.grand_total)
                    else:
                        amount=doc.outstanding_amount
                    amount_cent=int(amount*100)
                    #use new card item 
                    stripe_doc=frappe.get_doc("Stripe Settings",stripe_card.stripe_account )
                    pay_to = stripe_doc.pay_to
                    sender= stripe_doc.email_sending_account
                    email_template=stripe_doc.email_template
                    stripe.api_key = stripe_doc.secret_key
                    payment_intent = stripe.PaymentIntent.create(
                        customer=stripe_card.stripe_id,  
                        payment_method=payment_method_id, 
                        amount=amount_cent,  
                        currency=doc.currency.lower(),  
                        description=doc.doctype+"#"+doc.name,
                        confirm=True,  
                        automatic_payment_methods={
                            "enabled": True,
                            "allow_redirects": "never"
                        }
                    )
                    payment_ref=payment_intent.id
                    try : 
                        payment_entry = frappe.get_doc({
                            "doctype": "Payment Entry",
                            'party_type': 'Customer',
                            'party': doc.customer,
                            'paid_amount': amount,
                            'received_amount': amount,
                            'target_exchange_rate': 1.0,
                            "paid_from": doc.debit_to,
                            'paid_to_account_currency': doc.currency,
                            "paid_from_account_currency": doc.currency,
                            'paid_to': pay_to,
                            "reference_no": "**** "+stripe_card.last_digits+"/stripe:"+payment_ref,
                            "reference_date": dateStr,
                            'company': doc.company,
                            'mode_of_payment': 'Credit Card',
                            "status": "Submitted",
                            "docstatus": 1,
                            "references": [
                                {
                                    "reference_doctype": doc.doctype,
                                    "reference_name": doc.name,
                                    "total_amount": doc.grand_total,
                                    "allocated_amount":amount,
                                    "exchange_rate": 1.0,
                                    "exchange_gain_loss": 0.0,
                                    "parentfield": "references",
                                    "parenttype": "Payment Entry",
                                    "doctype": "Payment Entry Reference",
                                },
                            ],
                        })
                        payment_entry.save(ignore_permissions=True) 
                        if(email_template and sender ):
                            email_sender= frappe.db.get_value('Email Account', sender ,'email_id')
                            template_doc=frappe.get_doc("Email Template",email_template)
                            mail_template=template_doc.response
                            mail_subject=template_doc.subject
                            context={"amount":amount,
                                    "customer":doc.customer,
                                    "customer_name":doc.customer_name,
                                    "grand_total":doc.grand_total,
                                    "doctype":doc.doctype,
                                    "name":doc.name,
                                    "card_last_digits":stripe_card.last_digits,
                                    "stripe_payment_ref":payment_ref,
                                    "exp_card":stripe_card.last_digits
                                    }
                            mail_content =frappe.render_template(mail_template,context=context )
                            mail_subject =frappe.render_template(mail_subject,context=context )
                            frappe.sendmail(
                                    recipients=stripe_customer.email,
                                    sender=email_sender,
                                    subject=mail_subject,
                                    content=mail_content,     
                                    doctype=doc.doctype,
                                    name=doc.name,
                                    read_receipt= "0",
                                    print_letterhead= "1",
                                    now=True
                                    #now=True
                            )
                            frappe.get_doc({
                                "doctype": "Communication",
                                "communication_type": "Communication",
                                "content": mail_content,
                                "subject": mail_subject,
                                "sent_or_received": "Sent",
                                "recipients": stripe_customer.email,
                                "sender": email_sender,
                                "reference_doctype": doc.doctype,
                                "reference_name": doc.name,
                            }).insert(ignore_permissions=True)
                        frappe.db.commit()    
                    except e : 
                        frappe.msgprint("Exception  : " + str(e))
                    frappe.msgprint("Success : Invoice Payed using Stripe #"+payment_ref)
                    return
                except: 
                    payment_method_id=""
            frappe.msgprint("Error : Failed to process payment please check customer cards ")
            return
            
    except Exception as e :
        frappe.msgprint("Error : "+str(e))

@frappe.whitelist()
def hourly_process_payment():
    current_time = frappe.utils.now_datetime()
    stripe_customers=frappe.db.get_all("Stripe Customer",fields=["customer","process_delay"],filters={"auto_process":1},order_by='modified desc', limit_page_length=0)
    for sc in stripe_customers:
        sales=[]
        t= frappe.utils.add_to_date(current_time, hours=max(1,sc.process_delay)*(-1))
        customer_si=frappe.db.get_all("Sales Invoice",fields=["name"],filters={
            "customer": sc.customer  ,
            "modified":["<=",str(t)],
            "docstatus":1,
            "status": ["in", ["Partly Paid", "Unpaid", "Overdue"]]
            },order_by='modified', limit_page_length=0)
        sales.extend([{"name":si.name,"doctype":"Sales Invoice"} for si in customer_si])
        customer_so=frappe.db.get_all("Sales Order",fields=["name"],filters={
            "customer": sc.customer  ,
            "modified":["<=",str(t)],
            "docstatus":1,
            "status": ["in", ["Partly Paid", "Unpaid", "Overdue"]]
            },order_by='modified', limit_page_length=0)
        sales.extend([{"name":so.name,"doctype":"Sales Order"} for so in customer_so])
        for sale in sales :
            try:
                processPayment(sale["doctype"],sale["name"])
            except:
                "failed to process current invoice"




@frappe.whitelist()
def process_subscription(user_sub,sub_type):
    user_sub_doc=frappe.get_doc("User Subscription",user_sub)
    sub_type_doc=frappe.get_doc("Subscription Type",sub_type)
    stripe_customer_doc=frappe.get_doc("Stripe Customer",user_sub_doc.stripe_customer)
    filters={}
    if(stripe_customer_doc.stripe_account):
        filters={"name":stripe_customer_doc.stripe_account}
    stripe_settings=frappe.db.get_all("Stripe Settings",fields=["secret_key","pay_to","email_template","email_sending_account"],filters=filters,order_by='is_default desc,modified desc', limit_page_length=1)
    if(len(stripe_settings)==0):
        return {"message":"Please configure Stripe Settings first","status":0}
    stripe.api_key = stripe_settings[0]["secret_key"]
    pay_to = stripe_settings[0]["pay_to"]
    posting_date= frappe.utils.nowdate()
    due_date= frappe.utils.add_days(posting_date, +30)
    rate=20
    expiration_date=user_sub_doc.expiration_date
    item_prices_list=frappe.get_all("Item Price",fields=["price_list_rate"],filters={"item_code":sub_type_doc.item,"selling":1})
    if(len(item_prices_list)!=0):
        rate=item_prices_list[0]["price_list_rate"]
    invoice_doc = frappe.get_doc({
        'doctype': 'Sales Invoice',
        'company':sub_type_doc.company,
        'customer': stripe_customer_doc.customer,
        'posting_date': posting_date ,
        'due_date': due_date,
        "conversion_rate": 1,
        "plc_conversion_rate": 1,
        # TODO "docstatus": 1,
        'items': [
            {
                'item_code': sub_type_doc.item,
                'item_name': sub_type_doc.item,
                'qty': 1,
                'income_account': sub_type_doc.income_account,
                'conversion_factor': 1.0,
                'rate': rate,
                'amount': rate ,
            }]
    })
    invoice_doc.flags.ignore_permissions = True
    invoice_doc.set_missing_values()
    invoice_doc.calculate_taxes_and_totals()
    invoice_doc.save(ignore_permissions=True)
    result={}
    to_pay = invoice_doc.outstanding_amount
    if(invoice_doc.disable_rounded_total):
        to_pay =min(invoice_doc.outstanding_amount,invoice_doc.grand_total)
    result={"message":"Echec ","status":0}
    for stripe_card in stripe_customer_doc.cards_list:
        try:    
            payment_method_id=stripe_card.card_id
            amount_cent=int(to_pay *100)
            #use new card item
            stripe_doc=frappe.get_doc("Stripe Settings",stripe_card.stripe_account )
            pay_to = stripe_doc.pay_to
            stripe.api_key = stripe_doc.secret_key
            payment_intent = stripe.PaymentIntent.create(
                customer=stripe_card.stripe_id,  
                payment_method=payment_method_id, 
                amount=amount_cent,  
                currency=invoice_doc.currency.lower(),  
                description=invoice_doc.doctype+"#"+invoice_doc.name,
                confirm=True,  
                automatic_payment_methods={
                    "enabled": True,
                    "allow_redirects": "never"
                }
            )
            
            result= {"message":"Invoice Payed  #"+payment_intent.id,"status":1}
            try : 
                invoice_doc.submit()
                payment_entry = frappe.get_doc({
                    "doctype": "Payment Entry",
                    'party_type': 'Customer',
                    'party': invoice_doc.customer,
                    'paid_amount': to_pay,
                    'received_amount': to_pay,
                    'target_exchange_rate': 1.0,
                    "paid_from": invoice_doc.debit_to,
                    'paid_to_account_currency': invoice_doc.currency,
                    "paid_from_account_currency": invoice_doc.currency,
                    'paid_to': pay_to,
                    "reference_no": "**** "+stripe_card.last_digits+"/stripe:"+payment_intent.id,
                    "reference_date": posting_date ,
                    'company': invoice_doc.company,
                    'mode_of_payment': 'Credit Card',
                    "status": "Submitted",
                    "docstatus": 1,
                    "references": [
                        {
                            "reference_doctype": invoice_doc.doctype,
                            "reference_name": invoice_doc.name,
                            "total_amount": invoice_doc.grand_total,
                            "allocated_amount":to_pay,
                            "exchange_rate": 1.0,
                            "exchange_gain_loss": 0.0,
                            "parentfield": "references",
                            "parenttype": "Payment Entry",
                            "doctype": "Payment Entry Reference",
                        },
                    ],
                })
                payment_entry.save(ignore_permissions=True)  
                frappe.db.commit()   
                from_date=frappe.utils.nowdate() 
                if(expiration_date):
                    if(datetime.strptime(frappe.utils.nowdate() , "%Y-%m-%d").date() <= expiration_date): 
                        from_date= frappe.utils.add_days(str(expiration_date), 1)
                
                from_date_obj=datetime.strptime(from_date, "%Y-%m-%d").date() 
                sub_duration = calendar.monthrange(from_date_obj.year, from_date_obj.month)[1]-1
                if(sub_type_doc.unit  =="Year"): 
                    sub_duration=365-(from_date_obj.year%4!=0)
                to_date=frappe.utils.add_days(from_date,sub_duration)
                subscription_list=[{
                    "type":sub_type, 
                    "from":from_date, 
                    "to":to_date ,
                    "sales_invoice":invoice_doc.name, 
                    "payment_entry":payment_entry.name
                }]
                for sub in  user_sub_doc.subscription_list:
                    sub_dict=sub.as_dict()
                    sub_dict["idx"]=sub_dict["idx"]+1
                    subscription_list.append(sub_dict)
                user_sub_doc.set("subscription_list", subscription_list) 
                user_sub_doc.status="Subscribed"
                user_sub_doc.expiration_date=to_date 
                user_sub_doc.save(ignore_permissions=True)  
                mail_data={
                    "customer": invoice_doc.customer,
                    "to_pay": to_pay,
                    "card_last_digits": stripe_card.last_digits,
                    "payment_id": payment_intent.id,
                    "from_date": from_date,
                    "to_date": to_date
                }
                frappe.sendmail(
                            recipients=[user_sub_doc.user_id],
                            subject= sub_type_doc.submail_title,
                            content= str(sub_type_doc.submail_template).format(**mail_data),
                            now=True,
                            )
                        
            except stripe.error.StripeError as e:
                result["_exception"]="Exception : "+str(e)
            return result
        
        
        except stripe.error.StripeError as e:
            payment_method_id=""
            result= {"message":"Echec"+str(e),"status":0}
        except Exception as e: 
            payment_method_id=""
            result= {"message":"Echec"+str(e),"status":0}
            return result
    frappe.delete_doc("Sales Invoice", invoice_doc.name)
    return result 


@frappe.whitelist()
def daily_auto_subscription():     
    posting_date= frappe.utils.nowdate()        
    tomorrow=frappe.utils.add_days(posting_date,1)
    user_subsciptions=frappe.db.get_all("User Subscription",fields=["name","auto_subscription_type"],filters={ "auto_subscription":1, "auto_subscription_type":["is","set"],"expiration_date":[ "<=",tomorrow ]  },order_by='modified desc', limit_page_length=0)
    for user_sub in user_subsciptions:
        try:
            process_subscription(user_sub["name"],user_sub["auto_subscription_type"])
        except:
            message="Go skip for the next"


@frappe.whitelist()
def remove_card(customer_id,card_id):     
    user_roles = frappe.get_all("Has Role", filters={"parent": frappe.session.user}, fields=["role"])
    user_roles = [role.role for role in user_roles]
    is_admin = "System Manager" in user_roles or "Accounts Manager" in user_roles
    # you can allow guest by creating server script only but they dont have a direct access to it
    cmd=frappe.local.request.form.to_dict().get('cmd', '')

    if cmd.startswith('ipconnex_stripe_payment.ipconnex_stripe_payment.payement') and not is_admin:
        frappe.throw(_("This function is not allowed for Guest users"), frappe.PermissionError) 
    else : 
        try: 
            stripe_customers= frappe.db.get_all("Stripe Customer",fields=["name","stripe_account"],filters={"stripe_id":customer_id},order_by='modified desc', limit_page_length=1)
            if(len(stripe_customers)):
                if(stripe_customers[0]["stripe_account"]):
                    filters={"name":stripe_customers[0]["stripe_account"]}
            stripe_settings=frappe.db.get_all("Stripe Settings",fields=["secret_key"],filters=filters,order_by='is_default desc,modified desc', limit_page_length=1)
            if(len(stripe_settings)==0):
                return {"message":"Please configure Stripe Settings first","status":0}
            stripe.api_key = stripe_settings[0]["secret_key"]
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card"
            )
            for payment_method in payment_methods['data']:
                if payment_method['id'] == card_id:
                    stripe.PaymentMethod.detach(card_id)
                    return {"message":f"Card {card_id} successfully deleted !","status":1}
            return {"message":f"Card {card_id} not found !","status":0}
        except Exception as e:
            return {"message":f"An error occurred: {str(e)}","status":0}
        

@frappe.whitelist()
def setDefautStripeAccount(stripe_account):    
    user_roles = frappe.get_all("Has Role", filters={"parent": frappe.session.user}, fields=["role"])
    user_roles = [role.role for role in user_roles]
    is_admin = "System Manager" in user_roles or "Accounts Manager" in user_roles
    # you can allow guest by creating server script only but they dont have a direct access to it
    cmd=frappe.local.request.form.to_dict().get('cmd', '')

    if cmd.startswith('ipconnex_stripe_payment.ipconnex_stripe_payment.payement') and not is_admin:
        frappe.throw(_("This function is not allowed for Guest users"), frappe.PermissionError) 
    else : 
        
        stripe_settings=frappe.get_doc("Stripe Settings",stripe_account)
        
        stripe.api_key = stripe_settings.secret_key
        stripe_customers=frappe.get_all("Stripe Customer",fields=["name","email","customer"],filters={"stripe_account":""},order_by='modified desc', limit_page_length=0)
        for stripe_customer in stripe_customers:
            try: 
                customer_id=""
                customers = stripe.Customer.list(email=stripe_customer["email"]).auto_paging_iter()
                for customer in customers:
                    if customer.name == stripe_customer["customer"]:
                        customer_id=customer.id

                if(not customer_id):
                    new_customer = stripe.Customer.create(email=stripe_customer["email"], name=stripe_customer["customer"])
                    customer_id=new_customer.id

                setup_intent = stripe.SetupIntent.create(
                    customer=stripe_customer.stripe_id,
                    payment_method_types=['card']
                )
                stripe_customer.card_token=setup_intent.client_secret
                stripe_customer.save(ignore_permissions=True)
                frappe.db.set_value("Stripe Customer",stripe_customer["name"],"stripe_id",customer_id)
                frappe.db.set_value("Stripe Customer",stripe_customer["name"],"card_token",setup_intent.client_secret)
            except Exception as e:
                msg="do nothing"
        try: 
            stripe_accounts=frappe.get_all("Stripe Settings",fields=["name"],filters={"is_default":1}, limit_page_length=0)
            for stripe_acc in stripe_accounts:
                if(stripe_acc["name"]!=stripe_account):
                    frappe.db.set_value("Stripe Settings",stripe_acc["name"],"is_default",0)
            frappe.db.set_value("Stripe Settings",stripe_account,"is_default",1)
            frappe.db.commit()
            return {"message":f"Default Stripe Account has been set !","status":1}
        except Exception as e:
            return {"message":f"An error occurred: {str(e)}","status":0}







