import frappe

no_cache = 1

def get_context(context):
    frappe.clear_cache()
    frappe.cache().flushall()
    context.no_cache = 1
    stripe_settings=frappe.db.get_all("Stripe Settings",
            fields=["publishable_key"],order_by='modified', limit_page_length=0)
    if(len(stripe_settings)!=0):
        context.public_stripe =stripe_settings[0].publishable_key
    client_token = frappe.form_dict["token"]
    context.client_token = client_token
    stripe_customers=frappe.db.get_all("Stripe Customer",
                    filters={"card_token":client_token },
                    fields=["name","customer","email","card_token"],order_by='modified', limit_page_length=0)
    if(len(stripe_customers)!=0):
        context.customer=stripe_customers[0].customer
        context.email=stripe_customers[0].email
    context.no_cache = 1

