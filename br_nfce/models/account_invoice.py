# -*- coding: utf-8 -*-
# © 2016 Danimar Ribeiro, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re

from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    ind_final = fields.Selection(related='fiscal_position_id.ind_final')
    cnpj_cpf = fields.Char('CNPJ/CPF', size=18, copy=True)
    nome = fields.Char('Nome', size=100, copy=True)
    email = fields.Char('E-Mail', size=100, copy=True)
    
    @api.onchange('cnpj_cpf')
    def _onchange_cnpj_cpf(self):
        if self.cnpj_cpf:
            val = re.sub('[^0-9]', '', self.cnpj_cpf)
            if len(val) == 14:
                cnpj_cpf = "%s.%s.%s/%s-%s"\
                    % (val[0:2], val[2:5], val[5:8], val[8:12], val[12:14])
                self.cnpj_cpf = cnpj_cpf
            elif len(val) == 11:
                cnpj_cpf = "%s.%s.%s-%s"\
                    % (val[0:3], val[3:6], val[6:9], val[9:11])
                self.cnpj_cpf = cnpj_cpf
            else:
                raise UserError(u'Verifique CNPJ/CPF')

    def _prepare_edoc_vals(self, inv, inv_lines, serie_id):
        res = super(AccountInvoice, self)._prepare_edoc_vals(inv, inv_lines, serie_id)
        res['cnpj_cpf'] = self.cnpj_cpf
        res['nome'] = self.nome
        res['email'] = self.email
        return res
    