from odoo import fields, models

class BrHrCbo(models.Model):
    _name = "br_hr.cbo"
    _description = "Brazilian Classification of Occupation"

    code = fields.Integer(string='Code', required=True)
    name = fields.Char('Name', size=255, required=True, translate=True)
