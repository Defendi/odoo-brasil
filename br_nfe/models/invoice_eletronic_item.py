from odoo import api, fields, models

STATE = {'edit': [('readonly', False)]}


class InvoiceEletronicItem(models.Model):
    _inherit = "invoice.eletronic.item"

    @api.multi
    @api.depends('icms_cst', 'origem')
    def _compute_cst_danfe(self):
        for item in self:
            item.cst_danfe = (item.origem or '') + (item.icms_cst or '')

    cst_danfe = fields.Char(string="CST Danfe", compute="_compute_cst_danfe")

    cest = fields.Char(string="CEST", size=10, readonly=True, states=STATE,
                       help="Código Especificador da Substituição Tributária")
    classe_enquadramento_ipi = fields.Char(
        string="Classe Enquadramento", size=5, readonly=True, states=STATE)
    codigo_enquadramento_ipi = fields.Char(
        string="Classe Enquadramento", size=3, default='999',
        readonly=True, states=STATE)

    import_declaration_ids = fields.Many2many('br_account.import.declaration', string='Declaração de Importação')

    # ----------- ICMS INTERESTADUAL -----------
    tem_difal = fields.Boolean(string='Difal?', readonly=True, states=STATE)
    icms_bc_uf_dest = fields.Monetary(
        string='Base ICMS', readonly=True, states=STATE)
    icms_aliquota_fcp_uf_dest = fields.Float(
        string='% FCP', readonly=True, states=STATE)
    icms_aliquota_uf_dest = fields.Float(
        string='% ICMS destino', readonly=True, states=STATE)
    icms_aliquota_interestadual = fields.Float(
        string="% ICMS Inter", readonly=True, states=STATE)
    icms_aliquota_inter_part = fields.Float(
        string='% Partilha', default=100.0, readonly=True, states=STATE)
    icms_uf_remet = fields.Monetary(
        string='ICMS Remetente', readonly=True, states=STATE)
    icms_uf_dest = fields.Monetary(
        string='ICMS Destino', readonly=True, states=STATE)
    icms_fcp_uf_dest = fields.Monetary(
        string='Valor FCP', readonly=True, states=STATE)
    informacao_adicional = fields.Text(string="Informação Adicional")

    def _update_tax_from_fiscal_position(self,taxes):
        res = super(InvoiceEletronicItem,self)._update_tax_from_fiscal_position(taxes)
        icms_rule = taxes.get('icms_rule_id',False)
        if icms_rule:
            res['tem_difal'] = icms_rule.tem_difal
            res['icms_bc_uf_dest'] = 0.0 # Calcular
            res['icms_aliquota_fcp_uf_dest'] = icms_rule.tax_icms_fcp_id.amount if icms_rule.tax_icms_fcp_id else 0.0
            res['icms_aliquota_uf_dest'] = 0.0
            res['icms_aliquota_interestadual'] = icms_rule.tax_icms_inter_id.amount if icms_rule.tax_icms_inter_id else 0.0
            res['icms_aliquota_inter_part'] = 100.0
            res['icms_uf_remet'] = 0.0
            res['icms_uf_dest'] = 0.0 # Calcular
            res['icms_fcp_uf_dest'] = 0.0 # Calcular
        res['informacao_adicional'] = False # Verificar 
        return res