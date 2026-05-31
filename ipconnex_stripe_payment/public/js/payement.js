var script = document.createElement('script');
script.src = 'https://cdn.jsdelivr.net/npm/sweetalert2@10';
document.head.appendChild(script);


frappe.ui.form.on('Stripe Settings', {
    onload: function(frm) { 
        if (  frappe.user_roles.includes("System Manager")  || frappe.user_roles.includes("Accounts Manager") )
            { frm.set_df_property('secret_key', 'hidden', 0); } 
        else 
            { frm.set_df_property('secret_key', 'hidden', 1); } 
    } 
});
