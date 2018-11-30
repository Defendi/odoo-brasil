# -*- coding: utf-8 -*-
# © 2016 Danimar Ribeiro <danimaribeiro@gmail.com>, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


STATE = {'edit': [('readonly', False)]}


class InvoiceEletronic(models.Model):
    _inherit = 'invoice.eletronic'

    state = fields.Selection(selection_add=[('waiting', 'Esperando')])
    nfse_eletronic = fields.Boolean('Emite NFS-e?', readonly=True)
    verify_code = fields.Char(
        string=u'Código Autorização', size=20, readonly=True, states=STATE)
    numero_nfse = fields.Char(
        string=u"Número NFSe", size=50, readonly=True, states=STATE)

    @api.multi
    def _hook_validation(self):
        errors = super(InvoiceEletronic, self)._hook_validation()
        if self.nfse_eletronic:
            if not self.company_id.inscr_mun:
                errors.append(u'Inscrição municipal obrigatória')
        return errors

class InvoiceEletronicItem(models.Model):
    _inherit = 'invoice.eletronic.item'

    country_id = fields.Many2one('res.country', string=u'País retenção', ondelete='restrict')
    state_id = fields.Many2one("res.country.state", string='UF retenção', ondelete='restrict')
    city_id = fields.Many2one('res.state.city', u'Município retenção', ondelete='restrict')
