from __future__ import unicode_literals
import frappe, json
from frappe import _

def get_employee_leave_policy(employee):
	leave_policy = frappe.db.get_value("Employee", employee, "leave_policy")
	if not leave_policy:
		employee_grade = frappe.db.get_value("Employee", employee, "grade")
		if employee_grade:
			leave_policy = frappe.db.get_value("Employee Grade", employee_grade, "default_leave_policy")
			if not leave_policy:
				frappe.throw(_("Employee {0} of grade {1} have no default leave policy").format(employee, employee_grade))
	if leave_policy:
		return frappe.get_doc("Leave Policy", leave_policy)
	else:
		frappe.throw(_("Please set leave policy for employee {0} in Employee / Grade record").format(employee))