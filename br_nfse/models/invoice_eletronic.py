from odoo import api, fields, models

STATE = {'edit': [('readonly', False)]}

class InvoiceEletronic(models.Model):
    _inherit = 'invoice.eletronic'

    state = fields.Selection(selection_add=[('waiting', 'Esperando')])
    nfse_eletronic = fields.Boolean('Emite NFS-e?', readonly=True)
    verify_code = fields.Char(
        string='Código Autorização', size=20, readonly=True, states=STATE)
    numero_nfse = fields.Char(
        string="Número NFSe", size=50, readonly=True, states=STATE)

    @api.multi
    def _hook_validation(self):
        errors = super(InvoiceEletronic, self)._hook_validation()
        if self.nfse_eletronic:
            if not self.company_id.inscr_mun:
                errors.append('Inscrição municipal obrigatória')
        return errors

class InvoiceEletronicItem(models.Model):
    _inherit = 'invoice.eletronic.item'

    country_id = fields.Many2one('res.country', string='País retenção', ondelete='restrict')
    state_id = fields.Many2one("res.country.state", string='UF retenção', ondelete='restrict')
    city_id = fields.Many2one('res.state.city', 'Município retenção', ondelete='restrict')

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
