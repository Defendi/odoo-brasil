import logging
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp


_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.one
    @api.depends('invoice_line_ids.price_subtotal',
                 'invoice_line_ids.price_total',
                 'invoice_line_ids.ii_valor_despesas',
                 'tax_line_ids.amount',
                 'currency_id', 'company_id')
    def _compute_amount(self):
        super(AccountInvoice, self)._compute_amount()
        self.total_despesas_aduana = sum(l.ii_valor_despesas for l in self.invoice_line_ids)
        self.amount_total = self.total_bruto - self.total_desconto + self.total_tax + self.total_despesas_aduana
    
    import_id = fields.Many2one(comodel_name='br_account.import.declaration',string='Declaração Importação', readonly=True, states={'draft': [('readonly', False)]})
    total_despesas_aduana = fields.Float(string='Desp.Aduana ( + )', digits=dp.get_precision('Account'), store=True, compute="_compute_amount")

    def _prepare_invoice_line_from_di_line(self, line):
        data = {}
        invoice_line = self.env['account.invoice.line']
        account = invoice_line.get_invoice_line_account('in_invoice', line.product_id, False, self.env.user.company_id)
        data['product_id'] = line.product_id.id

        fpos = line.import_declaration_id.fiscal_position_id or line.import_declaration_id.partner_id.property_purchase_fiscal_position_id
        if fpos: 
            vals = fpos.map_tax_extra_values(line.product_id, line.import_declaration_id.partner_id, False, False, False, False)
            data['cfop_id'] = vals.get('cfop_id',False)
            data['icms_cst_normal'] = vals.get('icms_cst_normal',False)
            data['icms_csosn_simples'] = vals.get('icms_csosn_simples',False)
            data['icms_benef'] = vals.get('icms_benef',False)
            data['ipi_cst'] = vals.get('ipi_cst',False)
            data['ipi_codigo_enquadramento'] = vals.get('enq_ipi',False)
            data['ipi_classe_enquadramento'] = vals.get('cla_ipi',False)
            data['incluir_ipi_base'] = vals.get('incluir_ipi_base',False)
            data['pis_cst'] = vals.get('pis_cst',False)
            data['cofins_cst'] = vals.get('cofins_cst',False)
#             data['icms_rule_id'] = vals.get('icms_rule_id',False)
#             data['ipi_rule_id'] = vals.get('ipi_rule_id',False)
#             data['pis_rule_id'] = vals.get('pis_rule_id',False)
#             data['cofins_rule_id'] = vals.get('cofins_rule_id',False)
#             data['ii_rule_id'] = vals.get('ii_rule_id',False)
##             data['tax_icms_st_id'] = vals.get('tax_icms_st_id',False)

#             for key, value in vals.items():
#                 data[key] = value.id if isinstance(value, models.Model) else value

        
        data.update({
            'name': line.product_id.name,
            'fiscal_classification_id': line.product_id.fiscal_classification_id.id,
            'icms_origem': '1',
            'origin': line.import_declaration_id.name,
            'uom_id': line.uom_id.id,
            'product_id': line.product_id.id,
            'price_unit': line.price_unit_edoc,
            'quantity': line.quantity,
            'weight': line.amount_weight,
            'weight_net': line.amount_weight,
            'discount': 0.0,
            'outras_despesas': line.pis_valor + line.cofins_valor + line.siscomex_value,
            'icms_base_calculo_manual': line.icms_base_calculo,
            'tax_icms_id': line.tax_icms_id.id,
            'icms_aliquota': line.tax_icms_id.amount,
            'ipi_base_calculo_manual': line.ipi_base_calculo,
            'ipi_tipo': 'percent',
            'tax_ipi_id': line.tax_ipi_id.id,
            'pis_base_calculo_manual': line.pis_base_calculo,
            'pis_tipo': 'percent',
            'tax_pis_id': line.tax_pis_id.id,
            'cofins_base_calculo_manual': line.cofins_base_calculo,
            'cofins_tipo': 'percent',
            'tax_cofins_id': line.tax_cofins_id.id,
            'ii_base_calculo': line.ii_base_calculo,
            'tax_ii_id': line.tax_ii_id.id,
            'ii_aliquota': line.tax_ii_id.amount,
            'issqn_tipo': 'N',
            'icms_tipo_base': '3',
            'icms_st_tipo_base': '4',
            'company_fiscal_type': line.import_declaration_id.company_id.fiscal_type,
            'import_declaration_ids': [(6, 0, [line.import_declaration_id.id])],
            'calculate_tax': True,
#             'rule_id': False,
#             'cfop_id': False,
#             'fiscal_classification_id': False,
#             'product_type': 'product',
#             'fiscal_comment': False,
#             'icms_rule_id': False,
#             'icms_cst': '',
#             'icms_cst_normal': '',
#             'icms_benef': False,
#             'incluir_ipi_base': False,
#             'icms_base_calculo': 0.0,
#             'icms_valor': 0.0,
#             'icms_aliquota': 0.0,
#             'icms_aliquota_reducao_base': 0.0,
#             'icms_aliquota_diferimento': 0.0,
#             'icms_valor_diferido': 0.0,
#             'icms_valor_diferido_dif': 0.0,
#             'tax_icms_st_id': False,
#             'icms_st_valor': 0.0,
#             'icms_st_base_calculo': 0.0,
#             'icms_st_aliquota': 0.0,
#             'icms_st_aliquota_reducao_base': 0.0,
#             'icms_st_aliquota_mva': 0.0,
#             'icms_st_base_calculo_manual': 0.0,
#             'icms_substituto': 0.0,
#             'icms_bc_st_retido': 0.0,
#             'icms_aliquota_st_retido': 0.0,
#             'icms_st_retido': 0.0,
#             'tem_difal': False,
#             'icms_bc_uf_dest': 0.0,
#             'tax_icms_inter_id': False,
#             'tax_icms_intra_id': False,
#             'tax_icms_fcp_id': False,
#             'icms_aliquota_inter_part': 0.0,
#             'icms_fcp_uf_dest': 0.0,
#             'icms_uf_dest': 0.0,
#             'icms_uf_remet': 0.0,
#             'icms_csosn_simples': False,
#             'icms_aliquota_credito': 0.0,
#             'icms_valor_credito': 0.0,
#             'icms_st_aliquota_deducao': 0.0,
#             'issqn_rule_id': False,
#             'tax_issqn_id': False,
#             'service_type_id': False,
#             'issqn_base_calculo': 0.0,
#             'issqn_aliquota': 0.0,
#             'issqn_valor': 0.0,
#             'l10n_br_issqn_deduction': 0.0,
#             'ipi_rule_id': False,
#             'ipi_base_calculo': 0.0,
#             'ipi_reducao_bc': 0.0,
#             'ipi_valor': 0.0,
#             'ipi_aliquota': 0.0,
#             'ipi_cst': False,
#             'ipi_codigo_enquadramento': False,
#             'ipi_classe_enquadramento': False,
#             'pis_rule_id': False,
#             'pis_cst': False,
#             'pis_base_calculo': 0.0,
#             'pis_valor': 0.0,
#             'pis_aliquota': 0.0,
#             'cofins_rule_id': False,
#             'cofins_cst': False,
#             'cofins_base_calculo': 0.0,
#             'cofins_valor': 0.0,
#             'cofins_aliquota': 0.0,
#             'ii_rule_id': False,
#             'ii_valor': 0.0,
#             'ii_valor_iof': 0.0,
#             'ii_valor_despesas': 0.0,
#             'csll_rule_id': False,
#             'tax_csll_id': False,
#             'csll_base_calculo': 0.0,
#             'csll_valor': 0.0,
#             'csll_aliquota': 0.0,
#             'irrf_rule_id': False,
#             'tax_irrf_id': False,
#             'irrf_base_calculo': 0.0,
#             'irrf_valor': 0.0,
#             'irrf_aliquota': 0.0,
#             'inss_rule_id': False,
#             'tax_inss_id': False,
#             'inss_base_calculo': 0.0,
#             'inss_valor': 0.0,
#             'inss_aliquota': 0.0,
#             'outros_rule_id': False,
#             'tax_outros_id': False,
#             'outros_base_calculo': 0.0,
#             'outros_valor': 0.0,
#             'outros_aliquota': 0.0,
#             'informacao_adicional': False,
        })
        if account:
            data['account_id'] = account.id


        return data

    @api.onchange('import_id')
    def import_change(self):
        if not self.import_id:
            return {}
        self.env.context = dict(self.env.context, from_import_order_change=True)
        self.issuer = '1'
        fpos = self.import_id.fiscal_position_id or self.import_id.partner_id.property_purchase_fiscal_position_id
        if fpos:
            self.product_document_id = fpos.product_document_id
            self.product_serie_id = fpos.product_serie_id
        self.fiscal_position_id = fpos
        new_line = []
        new_line.append((5,))
        for line in self.import_id.line_ids:
            data = self._prepare_invoice_line_from_di_line(line)
            new_line.append((0, 0, data))
        self.invoice_line_ids = new_line
#         self._onchange_br_account_fiscal_position_id()

    @api.onchange('fiscal_position_id')
    def _onchange_br_account_fiscal_position_id(self):
        if not self.env.context.get('from_import_order_change', False):
            super(AccountInvoice,self)._onchange_br_account_fiscal_position_id()
        self.env.context = dict(self.env.context, from_import_order_change=False)

    @api.onchange('partner_id', 'company_id')
    def _onchange_partner_id(self):
        if not self.env.context.get('from_import_order_change', False):
            super(AccountInvoice,self)._onchange_partner_id()
            
class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'

    invoice_type = fields.Selection(related='invoice_id.type', store=True)
    import_export_group_ids = fields.One2many('account.export.group', 'account_inv_line_id', 'Grupo de Exportação')

    @api.onchange("import_export_group_ids")
    def _onchange_account_inv_line_id(self):
        res = {}
        import_exp_group = self.import_export_group_ids
        for import_line in import_exp_group:
            if import_line.key_nfe and not import_line.qty_export:
                clear_value = re.sub('[^0-9\.]', '', str(self.quantity)).split('.')                
                import_line.qty_export = clear_value[0]
            else:
                import_line.qty_export = import_line.qty_export

        return res

