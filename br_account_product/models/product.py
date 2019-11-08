from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    expense_is = fields.Boolean(string='Despesa')