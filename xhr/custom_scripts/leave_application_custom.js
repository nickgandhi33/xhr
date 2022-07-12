frappe.ui.form.on("Leave Application", {
	setup: function(frm) {
		frm.set_query("leave_type", function() {
			return {
				query: "xhr.utils.leave_application.list_leave_type",
			};
		});
	},

	make_dashboard: function(frm) {
                frm.set_query("leave_type", function() {
                        return {
                                query: "xhr.utils.leave_application.list_leave_type",
                        };
                });
        },

    refresh:  function(frm) {
		frm.set_df_property("leave_approver", 'read_only', 1)
        if (!(frappe.user.has_role("HR User") || frappe.user.has_role("HR Manager"))) {
			frm.toggle_display("naming_series", 0);
			frm.toggle_display("employee", 0);
			frm.toggle_display("employee_name", 0);
			frm.toggle_display("department", 0);
			// frm.toggle_display("leave_balance", 0);
			frm.toggle_display("section_break_7", 0);
			frm.toggle_display("salary_slip", 0);
			frm.toggle_display("sb10", 0);
			$('[data-fieldname="naming_series"]').closest(".form-column").hide();
		}
		if (frappe.user.has_role("Leave Approver")) {
			frm.toggle_display("section_break_7", 1);
		}
		hide_status(frm);
		approver_readonly(frm);
		set_default_employee(frm);

	},

	employee:  function(frm) {
		hide_status(frm);
	},
	leave_approver:  function(frm) {
		approver_readonly(frm);
	}
});

var set_default_employee = function(frm){
	if (frm.is_new()) {
		frappe.call({
			method: "xhr.utils.employee.get_employee_by_user_id",
			callback: function (r) {
				console.log(r);
				if (r.message) {
					frm.set_value("employee", r.message.name);
				}
			}
		});
	}	
}

var hide_status = function(frm){
	if(frm.doc.employee){
		frappe.call({
			method: "xhr.utils.employee.get_employee_by_user_id",
			callback: function (r) {
				if (r.message) {
					if(r.message.name == frm.doc.employee){
						frm.set_value("status", "Open");
						frm.toggle_display("status", 0);
					}else{
						frm.toggle_display("status", 1);
					}
				}
			}
		});
	}
}

var approver_readonly = function(frm){
	if (!frm.doc.__islocal){
		if(frm.doc.leave_approver == frappe.session.user){
			me.frm.set_df_property("leave_approver", "read_only", 1);
			me.frm.set_df_property("leave_type", "read_only", 1);
			me.frm.set_df_property("from_date", "read_only", 1);
			me.frm.set_df_property("to_date", "read_only", 1);
			me.frm.set_df_property("half_day", "read_only", 1);			
		}		
	}
}

