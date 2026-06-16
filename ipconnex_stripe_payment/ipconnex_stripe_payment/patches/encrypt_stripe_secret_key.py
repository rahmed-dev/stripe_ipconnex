# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
from frappe.utils.password import set_encrypted_password


def execute():
	"""Move plaintext Stripe Settings.secret_key into the encrypted __Auth store.

	secret_key became a Password field. The table column still holds the old
	plaintext written before the change; copy it into __Auth (encrypted with the
	site encryption_key) and mask the column. Idempotent — rows already masked
	are skipped, so re-running migrate is safe.
	"""
	rows = frappe.db.sql(
		"SELECT name, secret_key FROM `tabStripe Settings`", as_dict=True
	)
	for row in rows:
		secret = row.get("secret_key")
		if not secret:
			continue
		# Already migrated: the column holds only asterisks.
		if set(secret) == {"*"}:
			continue
		set_encrypted_password("Stripe Settings", row["name"], secret, "secret_key")
		frappe.db.set_value(
			"Stripe Settings",
			row["name"],
			"secret_key",
			"*" * len(secret),
			update_modified=False,
		)
	frappe.db.commit()
