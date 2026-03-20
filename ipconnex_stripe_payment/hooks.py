# -*- coding: utf-8 -*-
from __future__ import unicode_literals

app_name = "ipconnex_stripe_payment"
app_title = "IPCONNEX Stripe Payment"
app_publisher = "Frappe"
app_description = "A Stripe Payment module created by IPCONNEX"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "voip@ipconnex.com"
app_license = "MIT"


# include js in doctype views
doctype_js = {
	"Sales Invoice" : "public/js/payement.js",
	"Sales Order" : "public/js/payement.js",
    "Stripe Settings":"public/js/payement.js",
    "Payment Method":"public/js/payement.js",
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    "hourly": [
        "ipconnex_stripe_payment.ipconnex_stripe_payment.payement.hourly_process_payment",
        "ipconnex_stripe_payment.ipconnex_stripe_payment.payement.daily_auto_subscription",
    ]
}

doc_events = {
    "Sales Invoice": {
        "on_submit": "ipconnex_stripe_payment.ipconnex_stripe_payment.payement.checkProcessInvoice"
    },    
    "Sales Order": {
        "on_submit": "ipconnex_stripe_payment.ipconnex_stripe_payment.payement.checkProcessInvoice"
    }
}

app_install = "ipconnex_stripe_payment.ipconnex_stripe_payment.payement.setup_install"

