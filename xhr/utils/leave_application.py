from __future__ import unicode_literals
import frappe, json
from frappe import _
from xhr.utils.leave_period import overwrite_annual_allocation, get_leave_type_details
from erpnext.hr.utils import set_employee_name, get_leave_period
from erpnext.hr.doctype.leave_ledger_entry.leave_ledger_entry import create_leave_ledger_entry, delete_ledger_entry
from erpnext.hr.doctype.leave_application.leave_application import (is_lwp, get_leave_allocation_records, get_allocation_expiry,
	get_number_of_leave_days, get_leaves_for_period, get_pending_leaves_for_period, get_leave_approver)
from frappe.utils import cint, cstr, date_diff, flt, formatdate, getdate, get_link_to_form, \
	comma_or, get_fullname, add_days, nowdate, get_datetime_str, get_first_day, today
import math
from calendar import monthrange
from datetime import datetime, timedelta

@frappe.whitelist()
def on_update(doc, method):
	validate_leave_type(doc)
	validate_parent_leave_type(doc)

def leave_ledger_entry_on_submit(doc, method):
	parent_leave_type = frappe.db.get_value("Leave Type Policy", doc.leave_type, "parent_leave_type")
	if parent_leave_type and doc.leaves < 0:
		ledger = doc
		ledger.name = None
		ledger.leave_type = parent_leave_type

		frappe.get_doc(ledger).submit()

def leave_ledger_entry_on_trash(doc, method):
	parent_leave_type = frappe.db.get_value("Leave Type Policy", doc.leave_type, "parent_leave_type")
	if parent_leave_type:
		frappe.db.sql("""DELETE
		FROM `tabLeave Ledger Entry`
		WHERE
			`transaction_name`=%s """, (doc.transaction_name))
			
def get_remaining_leaves(allocation, leaves_taken, date, expiry):

	def _get_new_leaves_allocated(new_leaves_allocated, from_date):

		months = monthdelta(get_first_day(date), get_first_day(from_date)) + 1

		# count prorata_leaves_allocated
		leave_calculation_method = frappe.db.get_value("Leave Type Policy", allocation.leave_type, "leave_calculation_method") or "Full"
		if leave_calculation_method == "Accrual":
			if new_leaves_allocated >= 1:
				new_leaves_allocated = (new_leaves_allocated/12)*months
				new_leaves_allocated = _round_half_down(new_leaves_allocated)

		return new_leaves_allocated

	''' Returns minimum leaves remaining after comparing with remaining days for allocation expiry '''
	def _get_remaining_leaves(allocated_leaves, end_date):
		remaining_leaves = flt(allocated_leaves) + flt(leaves_taken)

		if remaining_leaves > 0:
			remaining_days = date_diff(end_date, date) + 1
			remaining_leaves = min(remaining_days, remaining_leaves)

		return remaining_leaves

	new_leaves_allocated = _get_new_leaves_allocated(allocation.new_leaves_allocated, allocation.from_date)

	# count unused_leaves
	if expiry and allocation.unused_leaves:
		unused_leaves = _get_remaining_leaves(allocation.unused_leaves, expiry)
	else:
		unused_leaves = allocation.unused_leaves
	
	total_leaves = flt(new_leaves_allocated) + flt(unused_leaves)

	return _get_remaining_leaves(total_leaves, allocation.to_date)

@frappe.whitelist()
def get_leave_balance_on(employee, leave_type, date, to_date=None, consider_all_leaves_in_the_allocation_period=False):
	'''
		Returns leave balance till date
		:param employee: employee name
		:param leave_type: leave type
		:param date: date to check balance on
		:param to_date: future date to check for allocation expiry
		:param consider_all_leaves_in_the_allocation_period: consider all leaves taken till the allocation end date
	'''

	if not to_date:
		to_date = nowdate()

	allocation_records = get_leave_allocation_records(employee, date, leave_type)
	allocation = allocation_records.get(leave_type, frappe._dict())

	end_date = allocation.to_date if consider_all_leaves_in_the_allocation_period else date
	expiry = get_allocation_expiry(employee, leave_type, to_date, date)

	leaves_taken = get_leaves_for_period(employee, leave_type, allocation.from_date, end_date)


	return get_remaining_leaves(allocation, leaves_taken, date, expiry)


def get_leave_balance_on_lwp(employee, leave_type, date, to_date=None, consider_all_leaves_in_the_allocation_period=False, leave_period = None, annual_allocation = None):
	'''
		Returns leave balance till date
		:param employee: employee name
		:param leave_type: leave type
		:param date: date to check balance on
		:param to_date: future date to check for allocation expiry
		:param consider_all_leaves_in_the_allocation_period: consider all leaves taken till the allocation end date
	'''

	if not to_date:
		to_date = nowdate()
	
	if not leave_period or not annual_allocation:
		return 0
	
	allocation = frappe._dict({
		"total_leaves_allocated": annual_allocation,
		"unused_leaves": 0,
		"new_leaves_allocated": annual_allocation,
		"from_date": leave_period.from_date,
		"to_date": leave_period.to_date,
		"leave_type": leave_type
	})

	end_date = allocation.to_date if consider_all_leaves_in_the_allocation_period else date
	expiry = get_allocation_expiry(employee, leave_type, to_date, date)

	leaves_taken = get_leaves_for_period(employee, leave_type, allocation.from_date, end_date)


	return get_remaining_leaves(allocation, leaves_taken, date, expiry)


def validate_leave_type(doc):
	if (doc.leave_type == "Annual Leave") and not doc.emergency and doc.status == "Open":
		days_before = add_days(today(), 5) 
		if doc.from_date < days_before: 
			frappe.throw(_("The start date has to be 5 days earlier from the date request"))

	leave_type = frappe.db.get_value("Leave Type Policy", doc.leave_type, "leave_type")

	if leave_type and doc.from_date and doc.to_date:
		doc.total_leave_days = get_number_of_leave_days(doc.employee, leave_type,
			doc.from_date, doc.to_date, doc.half_day, doc.half_day_date)
		
		if doc.total_leave_days <= 0:
			frappe.throw(_("The day(s) on which you are applying for leave are holidays. You need not apply for leave."))

		if not is_lwp(leave_type):
			doc.leave_balance = get_leave_balance_on(doc.employee, leave_type, doc.from_date, doc.to_date,
				consider_all_leaves_in_the_allocation_period=True)

			if doc.status != "Rejected" and (doc.leave_balance < doc.total_leave_days or not doc.leave_balance):
				if frappe.db.get_value("Leave Type", leave_type, "allow_negative"):
					frappe.msgprint(_("Note: There is not enough leave balance for Leave Type {0}")
						.format(leave_type))
				else:
					frappe.throw(_("There is not enough leave balance for Leave Type {0}")
						.format(leave_type))

def validate_parent_leave_type(doc):
	parent_leave_type = frappe.db.get_value("Leave Type Policy", doc.leave_type, "parent_leave_type")

	if parent_leave_type and doc.from_date and doc.to_date:
		doc.total_leave_days = get_number_of_leave_days(doc.employee, parent_leave_type,
			doc.from_date, doc.to_date, doc.half_day, doc.half_day_date)

		if doc.total_leave_days <= 0:
			frappe.throw(_("The day(s) on which you are applying for leave are holidays. You need not apply for leave."))

		if not is_lwp(parent_leave_type):
			doc.leave_balance = get_leave_balance_on(doc.employee, parent_leave_type, doc.from_date, doc.to_date,
				consider_all_leaves_in_the_allocation_period=True)
			if doc.status != "Rejected" and (doc.leave_balance < doc.total_leave_days or not doc.leave_balance):
				if frappe.db.get_value("Leave Type", parent_leave_type, "allow_negative"):
					frappe.msgprint(_("Note: There is not enough leave balance for Leave Type {0}")
						.format(parent_leave_type))
				else:
					frappe.throw(_("There is not enough leave balance for Leave Type {0}")
						.format(parent_leave_type))

def _round_half_down(n):
	if n - math.floor(n) < 0.5:
		return math.floor(n)
	return math.floor(n) + 0.5

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

def get_employee_leave_policy(employee):
	leave_policy = frappe.db.get_value("Employee", employee, "leave_policy")
	if not leave_policy:
		employee_grade = frappe.db.get_value("Employee", employee, "grade")
		if employee_grade:
			leave_policy = frappe.db.get_value("Employee Grade", employee_grade, "default_leave_policy")
			if not leave_policy:
				return None
	if leave_policy:
		return frappe.get_doc("Leave Policy", leave_policy)
	else:
		return None



@frappe.whitelist()
def get_leave_details(employee, date):
	allocation_records = get_leave_allocation_records(employee, date)
	leave_allocation = {}
	for d in allocation_records:
		allocation = allocation_records.get(d, frappe._dict())
		remaining_leaves = get_leave_balance_on(employee, d, date, to_date = allocation.to_date,
			consider_all_leaves_in_the_allocation_period=True)
		end_date = allocation.to_date
		leaves_taken = get_leaves_for_period(employee, d, allocation.from_date, end_date) * -1
		leaves_pending = get_pending_leaves_for_period(employee, d, allocation.from_date, end_date)

		leave_allocation[d] = {
			"total_leaves": allocation.total_leaves_allocated,
			"leaves_taken": leaves_taken,
			"pending_leaves": leaves_pending,
			"remaining_leaves": remaining_leaves}
	
	company=frappe.db.get_value("Global Defaults", None, "default_company")
	leave_policy = get_employee_leave_policy(employee)
	leave_period = get_leave_period(date, date, company)
	leave_type_details = get_leave_type_details()
	if leave_policy and leave_period:
		leave_period = leave_period[0]
		for leave_policy_detail in leave_policy.leave_policy_details:

			#overwrite by leave_type_policy_detail
			annual_allocation = leave_policy_detail.annual_allocation

			if annual_allocation and leave_type_details.get(leave_policy_detail.leave_type).is_lwp:

				total_leaves_allocated = annual_allocation
				leaves_taken = get_leaves_for_period(employee, leave_policy_detail.leave_type, leave_period.from_date, leave_period.to_date) * -1
				leaves_pending = get_pending_leaves_for_period(employee, leave_policy_detail.leave_type, leave_period.from_date, leave_period.to_date)
				remaining_leaves = get_leave_balance_on_lwp(employee, leave_policy_detail.leave_type, date, to_date = leave_period.to_date,
			consider_all_leaves_in_the_allocation_period=True, leave_period= leave_period, annual_allocation= annual_allocation)
			
				leave_allocation[leave_policy_detail.leave_type] = {
					"total_leaves": total_leaves_allocated,
					"leaves_taken": leaves_taken,
					"pending_leaves": leaves_pending,
					"remaining_leaves": remaining_leaves
				}

	user = frappe.session.user
	leave_allocation_sort = {}

	leave_sort_list = ["Annual Leave", "Replacement Leave", "Sick Leave", "Un Pay Leave", "Emergency Leave", "Hospitalization Leave", "Maternity Leave", "Paternity Leave", "Compassionate Leave"]

	if "Numac_Employee" in frappe.get_roles(user) and user != "Administrator":
		leave_sort_list = ["Annual Leave", "Replacement Leave"]

	for d in leave_sort_list:
		if leave_allocation.get(d):
			item = leave_allocation[d]
			#item["leave_type"] = d

			if ("HR Manager" not in frappe.get_roles(user)) or ("HR User" not in frappe.get_roles(user)):
				if d != "Annual Leave":
					item["total_leaves"] = "**"
					item["remaining_leaves"] = "**"

			leave_allocation_sort[d] = item
		
	ret = {
		'leave_allocation': leave_allocation_sort,
		'leave_approver': get_leave_approver(employee)
	}

	return ret

@frappe.whitelist(allow_guest=True)
def list_leave_type(doctype, txt, searchfield, page_len, start, filters):

	list = frappe.db.sql("""
		SELECT
			lt.name
		FROM
			`tabLeave Type` as lt
		LEFT JOIN
		(
			SELECT "Annual Leave" as s_name, 1 as s_sort UNION
			SELECT "Sick Leave" as s_name, 2 as s_sort UNION
			SELECT "Un Pay Leave" as s_name, 3 as s_sort UNION
			SELECT "Replacement Leave" as s_name, 4 as s_sort UNION
			SELECT "Compassionate Leave" as s_name, 5 as s_sort UNION
			SELECT "Maternity Leave" as s_name, 6 as s_sort UNION
			SELECT "Paternity Leave" as s_name, 7 as s_sort UNION
			SELECT "Hospitalization Leave" as s_name, 8 as s_sort UNION
			SELECT "Un Pay Sick Leave" as s_name, 9 as s_sort UNION
			SELECT "Un Pay-Hospitalization" as s_name, 10 as s_sort UNION
			SELECT "Un Pay-Others" as s_name, 11 as s_sort

		) as s ON s.s_name = lt.name
		WHERE 
			lt.name like %(txt)s
		ORDER BY -s_sort DESC	
		""",
		{
			'txt': "%%%s%%" % txt
		}
	)

	return list
