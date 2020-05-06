from odoo import api, fields, models, _
from odoo.exceptions import UserError

class CreateBatchNFSe(models.TransientModel):
    _name = 'wizard.create.batch.nfse'
    _description = """Assistente Cancelamento de NFS-e """

    format_file = fields.Selection([('xml','XML')], default='xml')
    date_scheduled = fields.Date(string='Data agendada',default=fields.Date.today)
    batch_type = fields.Selection([('tonew','Novas NFSe'),('tocancel','Cancelar NFSe')],string='Motivo',default='tonew')

    @api.multi
    def _browse_records(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []
        if self.batch_type == 'tonew':
            records = self.env['invoice.eletronic'].browse(active_ids).filtered(lambda x: x.nfse_eletronic and len(x.batch_id) == 0)
        else:
            records = self.env['invoice.eletronic'].browse(active_ids).filtered(lambda x: x.nfse_eletronic and len(x.batch_id) > 0 and len(x.batch_cancel_id) == 0)
        return records
    
    @api.model
    def _create_lote_id(self,serie):
        res = serie.lot_sequence_id.next_by_id()
        res = str(res).zfill(5)
        return res
    
    @api.multi
    def action_create_batch(self):
        records = self._browse_records()
        for nfse in records:
            lote = self.env['batch.invoice.eletronic'].search([('model','=',nfse.model),
                                                               ('state','=','draft')],limit=1)
            if len(lote) == 0:
                lote = self.env['batch.invoice.eletronic'].create({
                        'date': self.date_scheduled,
                        'batch_type': self.batch_type,
                        'name': self._create_lote_id(nfse.serie),
                        'state': 'draft',
                        'model': nfse.model,
                        'format_file11': self.format_file,
                    })
            
            if len(lote) > 0:
                if self.batch_type == 'tonew' and len(nfse.batch_id) == 0:
                    nfse.batch_id = lote
                    nfse.state = 'waiting'
                    nfse.data_agendada = self.date_scheduled
                elif self.batch_type == 'tocancel' and len(nfse.batch_id) > 0:
                    nfse.batch_cancel_id = lote
                    nfse.state = 'waiting'
