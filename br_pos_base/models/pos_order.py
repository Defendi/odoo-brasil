# -*- coding: utf-8 -*-

from openerp import models, fields, api
   
class PosOrder(models.Model):
    _inherit = 'pos.order'

    cnpj_cpf = fields.Char('CNPJ/CPF', size=18, copy=False, default='Não Indicado')
