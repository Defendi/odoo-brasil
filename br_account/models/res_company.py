from odoo import models, fields
from odoo.addons import decimal_precision as dp

COMPANY_FISCAL_TYPE = [
    ('1', 'Simples Nacional'),
    ('2', 'Simples Nacional – excesso de sublimite de receita bruta'),
    ('3', 'Regime Normal')
]

COMPANY_FISCAL_TYPE_DEFAULT = '3'


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _compute_crc(self):
        self.crc_formated = self.crc_number
        if bool(self.crc_state_id) and bool(self.crc_state_id.code):
            self.crc_formated += ' ' + self.crc_state_id.code

    fiscal_document_for_product_id = fields.Many2one(
        'br_account.fiscal.document', "Documento Fiscal para produto")

    annual_revenue = fields.Float(
        'Faturamento Anual', required=True,
        digits=dp.get_precision('Account'), default=0.00,
        help="Faturamento Bruto dos últimos 12 meses")
    fiscal_type = fields.Selection(
        COMPANY_FISCAL_TYPE, 'Regime Tributário', required=True,
        default=COMPANY_FISCAL_TYPE_DEFAULT)
    cnae_main_id = fields.Many2one(
        'br_account.cnae', 'CNAE Primário')
    cnae_secondary_ids = fields.Many2many(
        'br_account.cnae', 'res_company_br_account_cnae',
        'company_id', 'cnae_id', 'CNAE Secundários')

    icms_aliquota_credito = fields.Float(string="% Crédito de ICMS do SN")

    accountant_id = fields.Many2one('res.partner', string="Contador")
    crc_number  = fields.Char("CRC No.", size=30)
    crc_state_id = fields.Many2one("res.country.state", 'UF')
    crc_formated = fields.Char(string="CRC",compute='_compute_crc')
    director_id = fields.Many2one('res.partner', string="Gestor")
