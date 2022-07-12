from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.utils import getdate, cstr, add_days, date_diff, getdate, ceil, month_diff
from frappe.model.document import Document
from erpnext.hr.utils import validate_overlap
from xhr.utils.hr import get_employee_leave_policy
from frappe.utils.background_jobs import enqueue
from six import iteritems
from calendar import monthrange
from datetime import datetime, timedelta

@frappe.whitelist()
def grant_leave_allocation(leave_period_name, grade=None, department=None, designation=None, employee=None, carry_forward=0):

	leave_period = frappe.get_doc("Leave Period", leave_period_name)

	employee_records = get_employees({
		"grade": grade,
		"department": department,
		"designation": designation,
		"name": employee
	})

	if employee_records:
		# if len(employee_records) > 20:
		# 	frappe.enqueue(grant_leave_alloc_for_employees, timeout=600,
		# 		employee_records=employee_records, leave_period=leave_period, carry_forward=carry_forward)
		# else:
		grant_leave_alloc_for_employees(employee_records, leave_period, carry_forward)
	else:
		frappe.msgprint(_("No Employee Found"))

def get_employees(args):
	conditions, values = [], []
	for field, value in iteritems(args):
		if value:
			conditions.append("{0}=%s".format(field))
			values.append(value)

	condition_str = " and " + " and ".join(conditions) if len(conditions) else ""

	employees = frappe._dict(frappe.db.sql("select name, date_of_joining from tabEmployee where status='Active' {condition}" #nosec
		.format(condition=condition_str), tuple(values)))

	return employees

def grant_leave_alloc_for_employees(employee_records, leave_period, carry_forward=0):
	leave_allocations = []
	existing_allocations_for = get_existing_allocations(list(employee_records.keys()), leave_period.name)
	leave_type_details = get_leave_type_details()
	count = 0

	for employee in employee_records.keys():
		if employee in existing_allocations_for:
			continue
		count +=1
		leave_policy = get_employee_leave_policy(employee)
		if leave_policy:
			for leave_policy_detail in leave_policy.leave_policy_details:

				#overwrite by leave_type_policy_detail
				annual_allocation = overwrite_annual_allocation(leave_period, leave_policy_detail.leave_type, employee, leave_policy_detail.annual_allocation)

				frappe.errprint(leave_policy_detail.leave_type) 
				frappe.errprint(annual_allocation)

				if annual_allocation and not leave_type_details.get(leave_policy_detail.leave_type).is_lwp:
					leave_allocation = create_leave_allocation(employee, leave_policy_detail.leave_type,
						annual_allocation, leave_type_details, leave_period, carry_forward, employee_records.get(employee))
					leave_allocations.append(leave_allocation)

		frappe.db.commit()
		frappe.publish_progress(count*100/len(set(employee_records.keys()) - set(existing_allocations_for)), title = _("Allocating leaves..."))

	if leave_allocations:
		frappe.msgprint(_("Leaves has been granted sucessfully"))

def overwrite_annual_allocation(leave_period, leave_type, employee, leave_policy_annual_allocation):
	employee_grade = frappe.db.get_value("Employee", employee, "grade") or ""
	employee_gender = frappe.db.get_value("Employee", employee, "gender")
	date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")

	months = monthdelta(leave_period.from_date, date_of_joining)

	# check condition of employee
	leave_type_policy_gender = frappe.db.get_value("Leave Type Policy", leave_type, "gender")
	if leave_type_policy_gender and leave_type_policy_gender != employee_gender:
		return 0

	# check exist
	exist = frappe.db.exists("Leave Type Policy Detail", {"parent":leave_type})

	if not exist:
		return leave_policy_annual_allocation

	leave_type_policy = frappe.get_doc("Leave Type Policy", leave_type)

	annual_allocation = 0

	# by employee_grade
	annual_allocation_sql = frappe.db.sql("""
					select annual_allocation 
					from `tabLeave Type Policy Detail` 
					where parent = %(leave_type)s 
						and from_month <= %(months)s 
						and to_month >= %(months)s 
						and employee_grade = %(employee_grade)s """
					,{
						"leave_type" : leave_type,
						"months" : months,
						"employee_grade" : employee_grade
					})

	if annual_allocation_sql:
		annual_allocation = annual_allocation_sql[0][0]

	# Every One
	if not annual_allocation:
		annual_allocation_sql = frappe.db.sql("""
					select annual_allocation 
					from `tabLeave Type Policy Detail` 
					where parent = %(leave_type)s 
						and from_month <= %(months)s 
						and to_month >= %(months)s 
						and employee_grade is NULL """
					,{
						"leave_type" : leave_type,
						"months" : months
					})
		
		if annual_allocation_sql:
			annual_allocation = annual_allocation_sql[0][0]
	
	return annual_allocation

def get_existing_allocations(employees, leave_period):
	leave_allocations = frappe.db.sql_list("""
		SELECT DISTINCT
			employee
		FROM `tabLeave Allocation`
		WHERE
			leave_period=%s
			AND employee in (%s)
			AND carry_forward=0
			AND docstatus=1
	""" % ('%s', ', '.join(['%s']*len(employees))), [leave_period] + employees)
	if leave_allocations:
		frappe.msgprint(_("Skipping Leave Allocation for the following employees, as Leave Allocation records already exists against them. {0}")
			.format("\n".join(leave_allocations)))
	return leave_allocations

def get_leave_type_details():
	leave_type_details = frappe._dict()
	leave_types = frappe.get_all("Leave Type",
		fields=["name", "is_lwp", "is_earned_leave", "is_compensatory", "is_carry_forward", "expire_carry_forwarded_leaves_after_days"])
	for d in leave_types:
		leave_type_details.setdefault(d.name, d)
	return leave_type_details

def create_leave_allocation(employee, leave_type, new_leaves_allocated, leave_type_details, leave_period, carry_forward, date_of_joining):
	''' Creates leave allocation for the given employee in the provided leave period '''
	if carry_forward and not leave_type_details.get(leave_type).is_carry_forward:
		carry_forward = 0

	# Calculate leaves at pro-rata basis for employees joining after the beginning of the given leave period
	# if getdate(date_of_joining) > getdate(leave_period.from_date):
	# 	remaining_period = ((date_diff(leave_period.to_date, date_of_joining) + 1) / (date_diff(leave_period.to_date, leave_period.from_date) + 1))
	# 	new_leaves_allocated = ceil(new_leaves_allocated * remaining_period)

	frappe.errprint(new_leaves_allocated)

	# Earned Leaves and Compensatory Leaves are allocated by scheduler, initially allocate 0
	if leave_type_details.get(leave_type).is_earned_leave == 1 or leave_type_details.get(leave_type).is_compensatory == 1:
		new_leaves_allocated = 0

	allocation = frappe.get_doc(dict(
		doctype="Leave Allocation",
		employee=employee,
		leave_type=leave_type,
		from_date=leave_period.from_date,
		to_date=leave_period.to_date,
		new_leaves_allocated=new_leaves_allocated,
		leave_period=leave_period.name,
		carry_forward=carry_forward
		))
	allocation.save(ignore_permissions = True)
	allocation.submit()
	return allocation.name

def monthdelta(ed_date, st_date):
	d2 = getdate(ed_date)
	d1 = getdate(st_date)
	delta = 0

	while True:
		mdays = monthrange(d1.year, d1.month)[1]

		d1 += timedelta(days=mdays)
		if d1 <= d2:
			delta += 1
		else:
			break

	return delta