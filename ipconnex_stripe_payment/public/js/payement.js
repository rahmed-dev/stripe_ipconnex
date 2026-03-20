var script = document.createElement('script');
script.src = 'https://cdn.jsdelivr.net/npm/sweetalert2@10';
document.head.appendChild(script);


frappe.ui.form.on('Sales Invoice', {
        refresh: function(frm) {
            if( (frm.doc.status == 'Unpaid' || frm.doc.status == 'Overdue'|| frm.doc.status == 'Partly Paid') && frm.doc.customer_name && frm.doc.docstatus==1  ) {
                frm.add_custom_button(__('Pay Invoice'), function(event) {
                    $('button[data-label="Pay%20Invoice"]').prop('disabled', true);
                    frappe.call({
                        method:"ipconnex_stripe_payment.ipconnex_stripe_payment.payement.processPayment",
                        args:{
                            doctype:frm.doc.doctype ,
                            docname:frm.doc.name
                        },
                        callback: function(res) { 
                          if(res.message.status==1){ 
                            Swal.fire({
                            icon: 'success',
                            title: 'Success',
                            text: res.message.message,
                            });
                          }else{ 
                            Swal.fire({
                            icon: "warning",
                            title: "Warning",
                            text: res.message.message,
                          }); 
                        }
                      }
                    });
                });

            }
    }
});
frappe.ui.form.on('Sales Order', {
    refresh: function(frm) {
        frm.add_custom_button(__('Pay Invoice'), function(event) {
            $('button[data-label="Pay%20Invoice"]').prop('disabled', true);

            if(frm.doc.status !== 'Unpaid' && frm.doc.status !== 'Overdue') {
                frappe.msgprint('This invoice is ' + frm.doc.status)
                $('button[data-label="Pay%20Invoice"]').prop('disabled', false);
                return 0;
            }
            if( !frm.doc.customer_name || !frm.doc.name ){
                frappe.msgprint('Fill empty invoice values first!');
                $('button[data-label="Pay%20Invoice"]').prop('disabled', false);
                return 0;
            }    
            frappe.call({
                method:"ipconnex_stripe_payment.ipconnex_stripe_payment.payement.processPayment",
                args:{
                    doctype:frm.doc.doctype ,
                    docname:frm.doc.name
                },
                callback: function(res) { 
                  if(res.message.status==1){ 
                    Swal.fire({
                    icon: 'success',
                    title: 'Success',
                    text: res.message.message,
                    });
              
                  }else{ 
                    Swal.fire({
                    icon: "warning",
                    title: "Warning",
                    text: res.message.message,
                  }); 
              
                }
              }
            });
        })

    }
});

frappe.ui.form.on('Stripe Settings', { 
    onload: function(frm) { 
        if (  frappe.user_roles.includes("System Manager")  || frappe.user_roles.includes("Accounts Manager") )
            { frm.set_df_property('secret_key', 'hidden', 0); } 
        else 
            { frm.set_df_property('secret_key', 'hidden', 1); } 
    } 
});
