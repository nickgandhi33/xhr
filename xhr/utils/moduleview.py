import frappe
from frappe import _, msgprint, throw
from frappe.desk.moduleview import get_doctype_info, build_standard_config, add_custom_doctypes, add_section, \
	get_report_list, combine_common_sections, apply_permissions, filter_by_restrict_to_domain, get_disabled_reports
from frappe.utils import flt, has_common


@frappe.whitelist()
def get(module):
	"""Returns data (sections, list of reports, counts) to render module view in desk:
	`/desk/#Module/[name]`."""
	data = get_data(module)

	out = {
		"data": data
	}

	return out

def get_data(module, build=True):
	"""Get module data for the module view `desk/#Module/[name]`"""
	doctype_info = get_doctype_info(module)
	data = build_config_from_file(module)

	if not data:
		data = build_standard_config(module, doctype_info)
	else:
		add_custom_doctypes(data, doctype_info)

	add_section(data, _("Custom Reports"), "fa fa-list-alt",
		get_report_list(module))

	data = combine_common_sections(data)
	data = apply_permissions(data)

	# set_last_modified(data)

	if build:
		exists_cache = {}
		def doctype_contains_a_record(name):
			exists = exists_cache.get(name)
			if not exists:
				if not frappe.db.get_value('DocType', name, 'issingle'):
					exists = frappe.db.count(name)
				else:
					exists = True
				exists_cache[name] = exists
			return exists

		for section in data:
			for item in section["items"]:
				# Onboarding

				# First disable based on exists of depends_on list
				doctype = item.get("doctype")
				dependencies = item.get("dependencies") or None
				if not dependencies and doctype:
					item["dependencies"] = [doctype]

				dependencies = item.get("dependencies")
				if dependencies:
					incomplete_dependencies = [d for d in dependencies if not doctype_contains_a_record(d)]
					if len(incomplete_dependencies):
						item["incomplete_dependencies"] = incomplete_dependencies

				if item.get("onboard"):
					# Mark Spotlights for initial
					if item.get("type") == "doctype":
						name = item.get("name")
						count = doctype_contains_a_record(name)

						item["count"] = count

	return data

def build_config_from_file(module):
	"""Build module info from `app/config/desktop.py` files."""
	data = []
	module = frappe.scrub(module)

	for app in frappe.get_installed_apps():
		try:
			data += get_config(app, module)
		except ImportError:
			pass

	return filter_by_restrict_to_domain(data)

def get_config(app, module):
	"""Load module info from `[app].config.[module]`."""

	user = frappe.session.user
	Numac_Employee = False

	if user != "Administrator" and has_common(["Numac_Employee"], frappe.get_roles(user)):
		Numac_Employee = True

	# frappe.errprint(Numac_Employee)

	if app == "erpnext" and module in ["hr"] and Numac_Employee:
		config = frappe.get_module("{app}.config_erpnext.{module}".format(app="xhr", module=module))
	else:
		config = frappe.get_module("{app}.config.{module}".format(app=app, module=module))

	config = config.get_data()

	sections = [s for s in config if s.get("condition", True)]

	disabled_reports = get_disabled_reports()
	for section in sections:
		items = []
		for item in section["items"]:
			if item["type"]=="report" and item["name"] in disabled_reports:
				continue
			# some module links might not have name
			if not item.get("name"):
				item["name"] = item.get("label")
			if not item.get("label"):
				item["label"] = _(item.get("name"))
			items.append(item)
		section['items'] = items

	return sections