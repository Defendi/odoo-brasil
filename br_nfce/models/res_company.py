from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    id_token_csc = fields.Char(string="Identificador do CSC")
    csc = fields.Char(string='Código de Segurança do Contribuinte')

    danfe_model = fields.Selection([('central', 'Modelo QR Code Centralizado'),
                                    ('lateral', 'Modelo QR Code na lateral')],
                                       string="Mod. Danfe NFCe",
                                       default='central')
