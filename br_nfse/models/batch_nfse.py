from odoo import api, fields, models

BATCHSTATES = [
    ('draft', 'Aberto'),
    ('tosend', 'A Enviar'),
    ('done', 'Enviado'),
    ('cancel', 'Cancelado'),
    ('error', 'Errado'),
]

STATE = {'draft': [('readonly', False)]}

class BatchInvoiceEletronic(models.Model):
    _name = 'batch.invoice.eletronic'
    _description = """Lote de envio de NFS-e """
    #_order = 'name'

    state = fields.Selection(BATCHSTATES,string='Situação')
    date = fields.Date('Data', readonly=True, states=STATE, index=True)
    name = fields.Char(string='Código', size=10, readonly=True, states=STATE, index=True)
    model = fields.Selection([], string='Modelo', readonly=True, states=STATE)
    company_id = fields.Many2one('res.company', 'Empresa', readonly=True, states=STATE, default=lambda self: self.env.user.company_id.id)
    document_ids = fields.One2many("invoice.eletronic", "batch_id", string="Documentos")
