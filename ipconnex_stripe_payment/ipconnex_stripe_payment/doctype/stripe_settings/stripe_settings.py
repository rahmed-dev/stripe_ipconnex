
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document



class StripeSettings(Document):
    def get(self, *args, **kwargs):
        user_roles = frappe.get_all("Has Role", filters={"parent": frappe.session.user}, fields=["role"])
        user_roles = [role.role for role in user_roles]
        is_admin= "System Manager" in user_roles or "Accounts Manager" in user_roles
        if is_admin or frappe.local.request_ip.startswith("127.0.0"):
            pass
        else: 	
            self.secret_key = "*"*len(self.secret_key)
        return super().get(*args, **kwargs)
    

    def before_save(self):
        user_roles = frappe.get_all("Has Role", filters={"parent": frappe.session.user}, fields=["role"])
        user_roles = [role.role for role in user_roles]
        is_admin = "System Manager" in user_roles or "Accounts Manager" in user_roles
        if not is_admin:
            frappe.throw("The current user does not have the required admin role to edit Stripe Settings.")

    def before_insert(self):
        user_roles = frappe.get_all("Has Role", filters={"parent": frappe.session.user}, fields=["role"])
        user_roles = [role.role for role in user_roles]
        is_admin = "System Manager" in user_roles or "Accounts Manager" in user_roles
        if not is_admin:
            frappe.throw("The current user does not have the required admin role to create Stripe Settings.")