from odoo import fields, models

class BrAccountServiceType(models.Model):
    _inherit = 'br_account.service.type'

    codigo_tributacao_municipio = fields.Char(string="Cód. Tribut. Munic.", size=20, help="Código de Tributação no Munípio")
