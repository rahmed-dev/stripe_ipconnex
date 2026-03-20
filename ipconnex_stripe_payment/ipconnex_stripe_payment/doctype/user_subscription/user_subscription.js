var script = document.createElement("script");
script.src = "https://cdn.jsdelivr.net/npm/sweetalert2@10";
document.head.appendChild(script);

frappe.ui.form.on("User Subscription", {
  refresh: function (frm) {
    $("button[data-fieldname='subscribe']")
      .off("click")
      .on("click", function () {
        if (frm.doc.auto_subscription_type && frm.doc.user_id) {
          frappe.call({
            method:
              "ipconnex_stripe_payment.ipconnex_stripe_payment.payement.process_subscription",
            args: {
              user_sub: frm.doc.user_id,
              sub_type: frm.doc.auto_subscription_type,
            },
            callback: function (res) {
              if (res.message.status) {
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
        }
      });
  },
});
