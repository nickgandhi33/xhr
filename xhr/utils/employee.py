from __future__ import unicode_literals
import frappe, json
from frappe import _

@frappe.whitelist()
def get_employee_by_user_id(user_id=None):
	if not user_id:
		user_id = frappe.session.user 
	emp_id = frappe.db.get_value("Employee", {"user_id": user_id})
	if emp_id:
		employee = frappe.get_doc("Employee", emp_id)
		return employee
	return None