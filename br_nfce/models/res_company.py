# -*- coding: utf-8 -*-
# © 2016 Alessandro Fernandes Martini, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    CSC_ident = fields.Char(string="Identificador CSC")

    danfe_model = fields.Selection([('central', 'Modelo QR Code Centralizado'),
                                    ('lateral', 'Modelo QR Code na lateral')],
                                       string=u"Mod. Danfe NFCe",
                                       default='central')
