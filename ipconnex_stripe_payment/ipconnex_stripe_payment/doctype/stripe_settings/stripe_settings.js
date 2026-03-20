// Copyright (c) 2020, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Stripe Settings", {
  refresh: function (frm) {
    frm.set_query("pay_to", function () {
      return {
        filters: {
          is_group: 0,
        },
      };
    });
    frm.add_custom_button(__("Set as Default Stripe Account"), function () {
      frappe.call({
        method:
          "ipconnex_stripe_payment.ipconnex_stripe_payment.payement.setDefautStripeAccount",
        args: { stripe_account: frm.doc.name },
        callback: function (res) {
          if (res.message.status == 1) {
            frm.reload_doc();
            Swal.fire({
              icon: "success",
              title: "Success",
              text: res.message.message,
            });
          } else {
            Swal.fire({
              icon: "warning",
              title: "Warning",
              text: res.message.message,
            });
          }
        },
      });
    });
  },
});
