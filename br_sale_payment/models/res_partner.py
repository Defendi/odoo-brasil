# -*- coding: utf-8 -*-
# © 2017 Danimar Ribeiro, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    property_payment_mode_id = fields.Many2one('l10n_br.payment.mode', string=u"Modo de pagamento", company_dependent=True)
