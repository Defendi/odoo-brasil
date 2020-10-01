# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    days_lock_deadline = fields.Integer("Dias Cotação", default=7)

    def get_days_lock_deadline(self):
        params = self.env['ir.config_parameter'].sudo()
        return dict(
            days_lock_deadline=params.get_param('purchase.days_lock_deadline', default=False),
        )
    
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        params = self.env['ir.config_parameter'].sudo()
        params.set_param("purchase.days_lock_deadline", self.days_lock_deadline)
    
