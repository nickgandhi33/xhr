// Copyright (c) 2019, vinhnguyen.t090@gmail.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Leave Allocation Tool", {
	onload: function(frm) {
		if (!frm.doc.from_date) {
			frm.set_value('from_date', frappe.datetime.get_today());
		}
	},
	refresh: function(frm) {
		frm.disable_save();
	},
	company: function(frm) {
		if(frm.doc.company) {
			frm.set_query("department", function() {
				return {
					"filters": {
						"company": frm.doc.company,
					}
				};
			});
		}
	}
});
