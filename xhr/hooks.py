# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "xhr"
app_title = "Xhr"
app_publisher = "vinhnguyen.t090@gmail.com"
app_description = "X HR"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "vinhnguyen.t090@gmail.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/xhr/css/xhr.css"
# app_include_js = "/assets/xhr/js/xhr.js"

# include js, css files in header of web template
# web_include_css = "/assets/xhr/css/xhr.css"
# web_include_js = "/assets/xhr/js/xhr.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
doctype_js = {
    "Leave Period": "custom_scripts/leave_period_custom.js",
	"Leave Application": "custom_scripts/leave_application_custom.js"
}
# doctype_list_js = {
# 	"Leave Application": "custom_scripts/leave_application_list_custom.js"
# }
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "xhr.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "xhr.install.before_install"
# after_install = "xhr.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "xhr.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }
doc_events = {
	"Leave Application": {
		"on_update": "xhr.utils.leave_application.on_update"
	},
	"Leave Ledger Entry": {
		"on_submit": "xhr.utils.leave_application.leave_ledger_entry_on_submit",
		"on_trash": "xhr.utils.leave_application.leave_ledger_entry_on_trash"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"xhr.tasks.all"
# 	],
# 	"daily": [
# 		"xhr.tasks.daily"
# 	],
# 	"hourly": [
# 		"xhr.tasks.hourly"
# 	],
# 	"weekly": [
# 		"xhr.tasks.weekly"
# 	]
# 	"monthly": [
# 		"xhr.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "xhr.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"erpnext.hr.doctype.leave_application.leave_application.get_leave_balance_on": "xhr.utils.leave_application.get_leave_balance_on",
	"erpnext.hr.doctype.leave_application.leave_application.get_leave_details":  "xhr.utils.leave_application.get_leave_details",
	"frappe.desk.moduleview.get": "xhr.utils.moduleview.get" 
} 
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "xhr.task.get_dashboard_data"
# }

