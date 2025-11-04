app_name = "zoho_integration"
app_title = "Zoho Integration"
app_publisher = "itsyosefali"
app_description = "zoho integration for ERPNext"
app_email = "joeyxjoey123@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "zoho_integration",
# 		"logo": "/assets/zoho_integration/logo.png",
# 		"title": "Zoho Integration",
# 		"route": "/zoho_integration",
# 		"has_permission": "zoho_integration.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/zoho_integration/css/zoho_integration.css"
# app_include_js = "/assets/zoho_integration/js/zoho_integration.js"

# include js, css files in header of web template
# web_include_css = "/assets/zoho_integration/css/zoho_integration.css"
# web_include_js = "/assets/zoho_integration/js/zoho_integration.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "zoho_integration/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Customer": "public/js/customer.js",
	"Item": "public/js/item.js",
	"Sales Invoice": "public/js/sales_invoice.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "zoho_integration/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "zoho_integration.utils.jinja_methods",
# 	"filters": "zoho_integration.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "zoho_integration.install.before_install"
# after_install = "zoho_integration.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "zoho_integration.uninstall.before_uninstall"
# after_uninstall = "zoho_integration.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "zoho_integration.utils.before_app_install"
# after_app_install = "zoho_integration.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "zoho_integration.utils.before_app_uninstall"
# after_app_uninstall = "zoho_integration.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "zoho_integration.notifications.get_notification_config"

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

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Customer": {
		"after_insert": "zoho_integration.customer.push_customer_on_submit",
		"on_update": "zoho_integration.customer.push_customer_on_submit"
	},
	"Item": {
		"after_insert": "zoho_integration.item.push_item_on_submit",
		"on_update": "zoho_integration.item.push_item_on_submit"
	},
	"Sales Invoice": {
		"on_submit": "zoho_integration.invoice.send_invoice_on_update"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"zoho_integration.tasks.all"
# 	],
# 	"daily": [
# 		"zoho_integration.tasks.daily"
# 	],
# 	"hourly": [
# 		"zoho_integration.tasks.hourly"
# 	],
# 	"weekly": [
# 		"zoho_integration.tasks.weekly"
# 	],
# 	"monthly": [
# 		"zoho_integration.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "zoho_integration.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "zoho_integration.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "zoho_integration.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["zoho_integration.utils.before_request"]
# after_request = ["zoho_integration.utils.after_request"]

# Job Events
# ----------
# before_job = ["zoho_integration.utils.before_job"]
# after_job = ["zoho_integration.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"zoho_integration.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

fixtures = [
    "custom_field"
]