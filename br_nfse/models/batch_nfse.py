import re
from odoo import api, fields, models
from odoo.exceptions import UserError

BATCHSTATES = [
    ('draft', 'Provisório'),
    ('tosend', 'A Enviar'),
    ('done', 'Enviado'),
    ('cancel', 'Cancelado'),
    ('error', 'Erro'),
]

STATE = {'draft': [('readonly', False)]}

class BatchInvoiceEletronic(models.Model):
    _name = 'batch.invoice.eletronic'
    _description = """Lote de envio de NFS-e """
    _order = 'name,model,date'

    state = fields.Selection(BATCHSTATES, string='Situação', readonly=True)
    batch_type = fields.Selection([('tonew','Novas NFSe'),('tocancel','Cancelar NFSe')],string='Motivo',default='tonew',states=STATE,readonly=True)
    format_file = fields.Selection([('xml','XML'),('csv','CSV'),('txt','TXT')], default='xml', states=STATE, readonly=True)
    date = fields.Date('Data', readonly=True, states=STATE, index=True, default=fields.date.today())
    name = fields.Char(string='Código', size=10, readonly=True, states=STATE, index=True)
    protocolo = fields.Char(string='Protocolo', size=20, readonly=True, states={'draft': [('readonly', False)],'tosend': [('readonly', False)]}, index=True)
    model = fields.Selection([], string='Modelo', readonly=True, states=STATE)
    company_id = fields.Many2one('res.company', 'Empresa', readonly=True, states=STATE, default=lambda self: self.env.user.company_id.id)
    document_ids = fields.One2many("invoice.eletronic", "batch_id", string="Documentos",readonly=True)
    document_cancel_ids = fields.One2many("invoice.eletronic", "batch_cancel_id", string="Documentos", readonly=True)
    xml_to_send = fields.Binary(string="Arquivo a Enviar", readonly=True, states=STATE)
    xml_to_send_name = fields.Char(string="Nome Arquivo a ser enviado", size=100, readonly=True)
    return_xml = fields.Binary(string="Arquivo Retorno", readonly=True, states={'tosend': [('readonly', False)]})
    return_xml_name = fields.Char(string="Nome Arquivo de Retorno", size=100, readonly=True)
    observation = fields.Text(string="Observação",readonly=True)

    def _get_protocol(self,name):
        protocol = re.sub('[^0-9]', '', name)
        return protocol[:18]
        
    def _unlink_nfse(self):
        for nfse in self.document_ids:
            if nfse.state == 'waiting':
                nfse.state = 'draft'
                nfse.batch_id = False

    @api.multi
    def unlink(self):
        for lote in self:
            if lote.state not in ('draft'):
                raise UserError('O lote não pode ser excluído')
            lote._unlink_nfse()
        return super(BatchInvoiceEletronic,self).unlink()

    @api.multi
    def _process_return(self):
        pass
    
    @api.onchange('return_xml')
    def onchange_return_xml(self):
        if bool(self.return_xml):
            protocolo = self._get_protocol(self.return_xml_name)
            self.env.cr.execute("UPDATE batch_invoice_eletronic SET protocolo = '%s', return_xml_name = '%s'" % (protocolo,self.return_xml_name))
            self.protocolo = protocolo
        else:
            self.env.cr.execute("UPDATE batch_invoice_eletronic SET protocolo = Null, return_xml_name = Null")
            self.protocolo = False

    @api.multi
    def write(self, vals):
        res = super(BatchInvoiceEletronic,self).write(vals)
        return res
            
    @api.multi
    def _create_file(self):
        pass

    @api.multi
    def _cancel_lote(self):
        for nfse in self.document_ids:
            if self.state == 'draft':
                nfse.state = 'draft'
                nfse.batch_id = False
                self.state = 'cancel'
            elif self.state == 'tosend':
                self.state = 'cancel'
            elif self.state == 'done':
                nfse.state = 'draft'
                self.state = 'draft'
            elif self.state == 'error':
                self.state = 'cancel'

    @api.multi
    def action_create_file(self):
        for lote in self:
            lote._create_file()
            lote.state = 'tosend'

    @api.multi
    def action_process_file(self):
        for lote in self:
            lote._process_return()

    @api.multi
    def action_draft(self):
        for lote in self:
            lote.state = 'draft'

    @api.multi
    def action_cancel(self):
        for lote in self:
            lote._cancel_lote()

    @api.multi
    def action_error_nogroup(self):
        for lote in self:
            for nfse in lote.document_ids:
                nfse.state = 'draft'
#                 nfse.batch_id = False
            lote.state = 'error'

