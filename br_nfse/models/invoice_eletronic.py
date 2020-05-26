import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

STATE = {'edit': [('readonly', False)]}

class InvoiceEletronic(models.Model):
    _inherit = 'invoice.eletronic'

    state = fields.Selection(selection_add=[('waiting', 'Esperando')])
    nfse_eletronic = fields.Boolean('Emite NFS-e?', readonly=True)
    verify_code = fields.Char(string='Código Autorização', size=20, readonly=True, states=STATE)
    numero_nfse = fields.Char(string="Número NFSe", size=50, readonly=True, states=STATE)
    batch_id = fields.Many2one('batch.invoice.eletronic', 'Lote', readonly=True, states=STATE)
    batch_cancel_id = fields.Many2one('batch.invoice.eletronic', 'Lote', readonly=True, states=STATE)
    numero_lote_nfse = fields.Char(string="Número Lote NFSe", related='batch_id.name', size=10, readonly=True, states=STATE)

    @api.multi
    def _hook_validation(self):
        errors = super(InvoiceEletronic, self)._hook_validation()
        if self.nfse_eletronic:
            if not self.company_id.inscr_mun:
                errors.append('Inscrição municipal obrigatória')
        return errors

    @api.multi
    def cron_send_nfe(self, limit=50):
        inv_obj = self.env['invoice.eletronic'].with_context({'lang': self.env.user.lang, 'tz': self.env.user.tz})
        states = self._get_state_to_send()
        nfes = inv_obj.search([('state', 'in', states),
                               ('data_agendada', '<=', fields.Date.today()),
                               ('nfse_eletronic', '=', False)],
                              limit=limit)
        for item in nfes:
            try:
                _logger.info('Sending edoc id: %s (number: %s) by cron' % (
                    item.id, item.numero))
                item.action_send_eletronic_invoice()
            except Exception as e:
                item.log_exception(e)
                item.notify_user()
                _logger.error(
                    'Erro no envio de documento eletrônico', exc_info=True)

    def _gerar_xml_rps(self,rps_values):
        return False

    def _gerar_xml_lote(self,lote_values):
        return False

class InvoiceEletronicItem(models.Model):
    _inherit = 'invoice.eletronic.item'

    country_id = fields.Many2one('res.country', string='País retenção', ondelete='restrict')
    state_id = fields.Many2one("res.country.state", string='UF retenção', ondelete='restrict')
    city_id = fields.Many2one('res.state.city', 'Município retenção', ondelete='restrict')
    issqn_tipo = fields.Selection([('N', 'Normal'),('R', 'Retida'),('S', 'Substituta'),('I', 'Isenta')],string='Tipo do ISSQN',required=True, default='N')
    service_type_id = fields.Many2one('br_account.service.type','Tipo de Serviço')
    codigo_tributacao_municipio = fields.Char(string="Cód. Tribut. Munic.", size=20, readonly=True,help="Código de Tributação no Munípio", states=STATE)

    @api.onchange('issqn_tipo')
    def _onchange_issqn_tipo(self):
        if self.issqn_tipo in ('R','S'):
            self.country_id = self.invoice_id.partner_id.country_id
            self.state_id = self.invoice_id.partner_id.state_id
            self.city_id = self.invoice_id.partner_id.city_id
        else:
            self.country_id = self.invoice_id.company_id.country_id
            self.state_id = self.invoice_id.company_id.state_id
            self.city_id = self.invoice_id.company_id.city_id
