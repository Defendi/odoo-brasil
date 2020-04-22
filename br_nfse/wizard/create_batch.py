from odoo import api, fields, models, _
from odoo.exceptions import UserError

class CreateBatchNFSe(models.TransientModel):
    _name = 'wizard.create.batch.nfse'
    _description = """Assistente Cancelamento de NFS-e """

    @api.multi
    def browse_records(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        records = self.env['invoice.eletronic'].browse(active_ids).filtered(lambda x: not x.nfse_eletronic)
        return records
    
    @api.multi
    def action_create_batch(self):
        records = self.browse_records()
        
        for record in records:
            pass
            
            
