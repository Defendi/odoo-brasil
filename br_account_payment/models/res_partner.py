from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    sacador_id = fields.Many2one('res.partner', string='Sacador/Avalista')