from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    property_payment_mode_id = fields.Many2one('l10n_br.payment.mode', string="Modo de pagamento", company_dependent=True)
