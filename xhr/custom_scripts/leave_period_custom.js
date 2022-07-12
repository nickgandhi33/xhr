frappe.ui.form.on('Leave Period', {
    refresh: (frm)=>{
		if(!frm.is_new()) {
			frm.add_custom_button(__('Allocate'), function () {
				frm.trigger("allocate");
			});
		}
		frm.remove_custom_button("Grant Leaves");
    },
    allocate: function(frm) {
		var d = new frappe.ui.Dialog({
			title: __('Grant Leaves'),
			fields: [
				{
					"label": "Filter Employees By (Optional)",
					"fieldname": "sec_break",
					"fieldtype": "Section Break",
				},
				{
					"label": "Employee Grade",
					"fieldname": "grade",
					"fieldtype": "Link",
					"options": "Employee Grade"
				},
				{
					"label": "Department",
					"fieldname": "department",
					"fieldtype": "Link",
					"options": "Department"
				},
				{
					"fieldname": "col_break",
					"fieldtype": "Column Break",
				},
				{
					"label": "Designation",
					"fieldname": "designation",
					"fieldtype": "Link",
					"options": "Designation"
				},
				{
					"label": "Employee",
					"fieldname": "employee",
					"fieldtype": "Link",
					"options": "Employee"					
				},
				{
					"fieldname": "sec_break",
					"fieldtype": "Section Break",
				},
				{
					"label": "Add unused leaves from previous allocations",
					"fieldname": "carry_forward",
					"fieldtype": "Check",
					"default" : 1
				}
			],
			primary_action: function() {
				var data = d.get_values();
				data.leave_period_name = frm.doc.name;

				frappe.call({
					method: "xhr.utils.leave_period.grant_leave_allocation",
					args: data,
					freeze: true,
					callback: function(r) {
						if(!r.exc) {
							d.hide();
							frm.reload_doc();
						}
					}
				});
			},
			primary_action_label: __('Grant')
		});
		d.show();
    }
})
