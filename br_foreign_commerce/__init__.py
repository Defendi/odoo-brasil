# By Alexandre Defendi

from . import models
from odoo import api, SUPERUSER_ID


def post_init(cr, registry):

    env = api.Environment(cr, SUPERUSER_ID, {})

    DIs = env['br_account.import.declaration'].search([])
    for DI in DIs:
        DI.write({'active': False})
