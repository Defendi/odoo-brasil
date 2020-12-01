import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.multi
    def _load_template(self, company, code_digits=None,
                       transfer_account_id=None, account_ref=None,
                       taxes_ref=None):
        acc_ref, tax_ref = super(AccountChartTemplate, self)._load_template(
            company, code_digits, transfer_account_id, account_ref, taxes_ref)

        tax_tmpl_obj = self.env['account.tax.template']
        tax_obj = self.env['account.tax']
        for key, value in tax_ref.items():
            tax_tmpl_id = tax_tmpl_obj.browse(key)
            tax_obj.browse(value).write({
                'deduced_account_id': acc_ref.get(
                    tax_tmpl_id.deduced_account_id.id, False),
                'refund_deduced_account_id': acc_ref.get(
                    tax_tmpl_id.refund_deduced_account_id.id, False)
            })
        return acc_ref, tax_ref


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    deduced_account_id = fields.Many2one(
        'account.account.template', string="Conta de Dedução da Venda")
    refund_deduced_account_id = fields.Many2one(
        'account.account.template', string="Conta de Dedução do Reembolso")
    domain = fields.Selection([('icms', 'ICMS'),
                               ('icmsst', 'ICMS ST'),
                               ('pis', 'PIS'),
                               ('cofins', 'COFINS'),
                               ('ipi', 'IPI'),
                               ('issqn', 'ISSQN'),
                               ('ii', 'II'),
                               ('icms_inter', 'Difal - Alíquota Inter'),
                               ('icms_intra', 'Difal - Alíquota Intra'),
                               ('fcp', 'FCP'),
                               ('fcpst', 'FCP ST'),
                               ('csll', 'CSLL'),
                               ('irrf', 'IRRF'),
                               ('inss', 'INSS'),
                               ('outros', 'Outros')], string="Tipo")
    amount_type = fields.Selection(selection_add=[('icmsst', 'ICMS ST')])

    def _get_tax_vals(self, company, tax_template_to_tax):
        res = super(AccountTaxTemplate, self)._get_tax_vals(
            company, tax_template_to_tax)
        res['domain'] = self.domain
        res['amount_type'] = self.amount_type
        return res


class AccountTax(models.Model):
    _inherit = 'account.tax'

    deduced_account_id = fields.Many2one(
        'account.account', string="Conta de Dedução da Venda")
    refund_deduced_account_id = fields.Many2one(
        'account.account', string="Conta de Dedução do Reembolso")
    domain = fields.Selection([('icms', 'ICMS'),
                               ('icmsst', 'ICMS ST'),
                               ('pis', 'PIS'),
                               ('cofins', 'COFINS'),
                               ('ipi', 'IPI'),
                               ('issqn', 'ISSQN'),
                               ('ii', 'II'),
                               ('icms_inter', 'Difal - Alíquota Inter'),
                               ('icms_intra', 'Difal - Alíquota Intra'),
                               ('fcp', 'FCP'),
                               ('fcpst', 'FCP ST'),
                               ('csll', 'CSLL'),
                               ('irrf', 'IRRF'),
                               ('inss', 'INSS'),
                               ('outros', 'Outros')], string="Tipo")
    amount_type = fields.Selection(selection_add=[('icmsst', 'ICMS ST')])
    difal_por_dentro = fields.Boolean(string="Calcular Difal por Dentro?")
    icms_st_incluso = fields.Boolean(
        string="Incluir ICMS ST na Base de Calculo?")
    allow_credit_utilization = fields.Boolean(
        string="Permite Aprov. de Crédito")

    @api.onchange('domain')
    def _onchange_domain_tax(self):
        if self.domain in ('icms', 'pis', 'cofins', 'issqn', 'ii',
                           'icms_inter', 'icms_intra', 'fcp', 'fcpst'):
            self.price_include = True
            self.amount_type = 'division'
        if self.domain in ('icmsst', 'ipi'):
            self.price_include = False
            self.include_base_amount = False
            self.amount_type = 'division'
        if self.domain == 'icmsst':
            self.amount_type = 'icmsst'

    @api.onchange('deduced_account_id')
    def _onchange_deduced_account_id(self):
        self.refund_deduced_account_id = self.deduced_account_id

    def _tax_vals(self, tax):
        return {
            'id': tax.id,
            'name': tax.name,
            'sequence': tax.sequence,
            'account_id': tax.account_id.id,
            'refund_account_id': tax.refund_account_id.id,
            'allow_credit_utilization': tax.allow_credit_utilization,
            'analytic': tax.analytic
        }

    def _compute_ipi(self, price_base):
        precision = self.env['decimal.precision'].precision_get('Account')
        ipi_tax = self.filtered(lambda x: x.domain == 'ipi')
        if not ipi_tax:
            return []
        vals = self._tax_vals(ipi_tax)
        base_tax = self.calc_ipi_base(price_base)
        vals['domain'] = 'ipi'
        if 'ipi_base_calculo_manual' in self.env.context and\
                self.env.context['ipi_base_calculo_manual'] > 0:
            vals['base'] = self.env.context['ipi_base_calculo_manual']
        else:
            vals['base'] = base_tax
        vals['amount'] = round(ipi_tax._compute_amount(vals['base'], 1.0),precision)
        return [vals]

    def calc_ipi_base(self, price_base):
        reducao_ipi = 0.0
        if "ipi_reducao_bc" in self.env.context:
            reducao_ipi = self.env.context['ipi_reducao_bc']
        base_ipi = price_base
        if "valor_frete" in self.env.context:
            base_ipi += self.env.context["valor_frete"]
        if "valor_seguro" in self.env.context:
            base_ipi += self.env.context["valor_seguro"]
        if "outras_despesas" in self.env.context:
            base_ipi += self.env.context["outras_despesas"]

        return base_ipi * (1 - (reducao_ipi / 100.0))

    def _compute_icms(self, price_base, ipi_value):
        precision = self.env['decimal.precision'].precision_get('Account')
        icms_tax = self.filtered(lambda x: x.domain == 'icms')
        if not icms_tax:
            return []
        vals = self._tax_vals(icms_tax)

        vals['domain'] = 'icms'
        vals['operacao'] = 0.00
        base_icms = self.calc_icms_base(price_base, ipi_value)

        diferimento_icms = False
        if "icms_aliquota_diferimento" in self.env.context:
            diferimento_icms = self.env.context['icms_aliquota_diferimento']

        if 'icms_base_calculo_manual' in self.env.context and self.env.context['icms_base_calculo_manual'] > 0:
            vals['amount'] = icms_tax._compute_amount(self.env.context['icms_base_calculo_manual'], 1.0)
            vals['base'] = self.env.context['icms_base_calculo_manual']
        else:
            vals['amount'] = icms_tax._compute_amount(base_icms, 1.0)
            vals['base'] = base_icms
        if diferimento_icms and diferimento_icms > 0.0:
            vals['operacao'] = vals['amount']
            vals['amount'] *= 1 - (diferimento_icms / 100.0)
        vals['amount'] = round(vals['amount'],precision)
        return [vals]

    def calc_icms_base(self, price_base, ipi_value):
        base_icms = price_base
        incluir_ipi = False
        reducao_icms = 0.0
        if 'incluir_ipi_base' in self.env.context:
            incluir_ipi = self.env.context['incluir_ipi_base']
        if "icms_aliquota_reducao_base" in self.env.context:
            reducao_icms = self.env.context['icms_aliquota_reducao_base']

        if incluir_ipi:
            base_icms += ipi_value
        if "valor_frete" in self.env.context:
            base_icms += self.env.context["valor_frete"]
        if "valor_seguro" in self.env.context:
            base_icms += self.env.context["valor_seguro"]
        if "outras_despesas" in self.env.context:
            base_icms += self.env.context["outras_despesas"]

        return base_icms * (1 - (reducao_icms / 100.0))

    def _compute_icms_st(self, price_base, ipi_value, icms_value, quantity, factor_uom=None, factor_imp=None, uom_imposto=None):
        precision = self.env['decimal.precision'].precision_get('Account')
        icmsst_tax = self.filtered(lambda x: x.domain == 'icmsst')
        if not icmsst_tax:
            return []
        
        vals = self._tax_vals(icmsst_tax)
        vals['domain'] = 'icmsst'

        base_icms = price_base
        base_icmsst = price_base + ipi_value
        reducao_icmsst = 0.0
        aliquota_mva = 0.0
        icms_st_tipo_base = 4
        preco_pauta = 0.0
        deducao_st_simples = 0.0

        if "icms_st_aliquota_reducao_base" in self.env.context:
            reducao_icmsst = self.env.context['icms_st_aliquota_reducao_base']
        if "icms_st_aliquota_mva" in self.env.context:
            aliquota_mva = self.env.context['icms_st_aliquota_mva']
        if "valor_frete" in self.env.context:
            base_icmsst += self.env.context["valor_frete"]
        if "valor_seguro" in self.env.context:
            base_icmsst += self.env.context["valor_seguro"]
        if "outras_despesas" in self.env.context:
            base_icmsst += self.env.context["outras_despesas"]
        if "icms_st_tipo_base" in self.env.context:
            icms_st_tipo_base = self.env.context['icms_st_tipo_base']
        if "icms_st_preco_pauta" in self.env.context:
            preco_pauta = self.env.context['icms_st_preco_pauta']
        if "icms_st_aliquota_deducao" in self.env.context:
            deducao_st_simples = self.env.context["icms_st_aliquota_deducao"]
        if 'icms_st_base_calculo_manual' in self.env.context and \
                self.env.context['icms_st_base_calculo_manual'] > 0:
            base_icms = self.env.context['icms_base_calculo_manual']
            base_icmsst = self.env.context['icms_st_base_calculo_manual']
            base_icmsst *= 1 - (reducao_icmsst / 100.0)  # Redução
        else:
            base_icmsst *= 1 - (reducao_icmsst / 100.0)  # Redução
            base_icmsst *= 1 + aliquota_mva / 100.0  # Aplica MVA

        if factor_uom:
            quantity = quantity * factor_uom
        else:
            factor_uom = 1

        if factor_imp:
            if uom_imposto == None or uom_imposto.factor == 0:
                uom_imposto.factor = 1
            preco_pauta = preco_pauta / uom_imposto.factor * factor_imp

        base_icmsst_pauta = preco_pauta * quantity

        if deducao_st_simples:
            icms_value = base_icms * (deducao_st_simples / 100.0)

        valor_unitario = 0
        if quantity > 0:
            valor_unitario = (price_base / quantity / factor_uom)
        else:
            valor_unitario = preco_pauta
        if valor_unitario == 0 or valor_unitario > preco_pauta:
            icms_st_tipo_base = '4'
            icmsst = round(
                (base_icmsst * (icmsst_tax.amount / 100.0)) - icms_value, 2)
        else:
            icms_st_tipo_base = '5'
            base_icmsst = base_icmsst_pauta
            icmsst = round(
                (base_icmsst_pauta * (icmsst_tax.amount / 100.0)) - icms_value, 2)

        vals['amount'] = round(icmsst,precision) if icmsst >= 0.0 else 0.0
        vals['base'] = base_icmsst
        vals['tipo_base_st'] = icms_st_tipo_base

        return [vals]

    def _compute_difal(self, price_base, ipi_value, tem_difal=True):
        precision = self.env['decimal.precision'].precision_get('Account')
        icms_inter = self.filtered(lambda x: x.domain == 'icms_inter')
        icms_intra = self.filtered(lambda x: x.domain == 'icms_intra')
        icms_fcp = self.filtered(lambda x: x.domain == 'fcp')
        
        if not icms_inter or not icms_intra:
            return []
        vals_fcp = None
        vals_inter = self._tax_vals(icms_inter)
        vals_inter['domain'] = 'icms_inter'
        vals_intra = self._tax_vals(icms_intra)
        vals_intra['domain'] = 'icms_intra'
        if icms_fcp:
            vals_fcp = self._tax_vals(icms_fcp)
        base_icms = price_base + ipi_value
        reducao_icms = 0.0
        if "icms_aliquota_reducao_base" in self.env.context:
            reducao_icms = self.env.context['icms_aliquota_reducao_base']

        if "valor_frete" in self.env.context:
            base_icms += self.env.context["valor_frete"]
        if "valor_seguro" in self.env.context:
            base_icms += self.env.context["valor_seguro"]
        if "outras_despesas" in self.env.context:
            base_icms += self.env.context["outras_despesas"]

        base_icms *= 1 - (reducao_icms / 100.0)
        interestadual = icms_inter._compute_amount(base_icms, 1.0)

        if icms_inter.difal_por_dentro or icms_intra.difal_por_dentro:
            base_icms = base_icms - interestadual
            base_icms = base_icms / (1 - (icms_intra.amount) / 100)

        interno = icms_intra._compute_amount(base_icms, 1.0)

        if 'icms_aliquota_inter_part' in self.env.context:
            icms_inter_part = self.env.context["icms_aliquota_inter_part"]
        else:
            icms_inter_part = 100.0

        
        if tem_difal is True: 
            _logger.info('>>> Tem difal')
            vals_inter['base'] = base_icms
            vals_intra['base'] = base_icms
    
            vals_inter['amount'] = round((interno - interestadual) *
                                         (100 - icms_inter_part) / 100, precision)
            vals_intra['amount'] = round((interno - interestadual) *
                                         icms_inter_part / 100, precision)
        else:
            vals_inter['base'] = 0.0
            vals_intra['base'] = 0.0
            vals_inter['amount'] = 0.0
            vals_intra['amount'] = 0.0

        taxes = [vals_inter, vals_intra]
        if vals_fcp:
            fcp = icms_fcp._compute_amount(base_icms, 1.0) or 0.0
            vals_fcp['amount'] = fcp
            vals_fcp['base'] = base_icms
            taxes += [vals_fcp]
        return taxes

    def _compute_pis_cofins(self, price_base):
        precision = self.env['decimal.precision'].precision_get('Account')
        pis_cofins_tax = self.filtered(lambda x: x.domain in ('pis', 'cofins'))
        if not pis_cofins_tax:
            return []
        taxes = []
        for tax in pis_cofins_tax:
            vals = self._tax_vals(tax)
            vals['domain'] = tax.domain
            if tax.domain == 'pis':
                if 'pis_base_calculo_manual' in self.env.context and\
                        self.env.context['pis_base_calculo_manual'] > 0:
                    vals['amount'] = tax._compute_amount(
                        self.env.context['pis_base_calculo_manual'], 1.0)
                    vals['base'] = self.env.context['pis_base_calculo_manual']
                else:
                    vals['amount'] = tax._compute_amount(price_base, 1.0)
                    vals['base'] = price_base
            if tax.domain == 'cofins':
                if 'cofins_base_calculo_manual' in self.env.context and\
                        self.env.context['cofins_base_calculo_manual'] > 0:
                    vals['amount'] = tax._compute_amount(
                        self.env.context['cofins_base_calculo_manual'], 1.0)
                    vals['base'] = self.env.context[
                        'cofins_base_calculo_manual']
                else:
                    vals['amount'] = tax._compute_amount(price_base, 1.0)
                    vals['base'] = price_base
            vals['amount'] = round(vals['amount'],precision)
            taxes.append(vals)
        return taxes

    def _compute_ii(self, price_base):
        precision = self.env['decimal.precision'].precision_get('Account')
        ii_tax = self.filtered(lambda x: x.domain == 'ii')
        if not ii_tax:
            return []
        vals = self._tax_vals(ii_tax)
        vals['domain'] = 'ii'
        if "ii_base_calculo" in self.env.context and \
                self.env.context['ii_base_calculo'] > 0:
            price_base = self.env.context["ii_base_calculo"]
        vals['amount'] = round(ii_tax._compute_amount(price_base, 1.0),precision)
        vals['base'] = price_base
        return [vals]

    def _compute_issqn(self, price_base):
        precision = self.env['decimal.precision'].precision_get('Account')
        issqn_tax = self.filtered(lambda x: x.domain == 'issqn')
        if not issqn_tax:
            return []
        issqn_deduction = self.env.context.get('l10n_br_issqn_deduction', 0.0)
        price_base *= (1 - (issqn_deduction / 100.0))
        vals = self._tax_vals(issqn_tax)
        vals['domain'] = 'issqn'
        vals['amount'] = round(issqn_tax._compute_amount(price_base, 1.0),precision)
        vals['base'] = price_base
        return [vals]

    def _compute_retention(self, price_base):
        precision = self.env['decimal.precision'].precision_get('Account')
        retention_tax = self.filtered(
            lambda x: x.domain in ('csll', 'irrf', 'inss', 'outros'))
        if not retention_tax:
            return []
        taxes = []
        for tax in retention_tax:
            vals = self._tax_vals(tax)
            vals['domain'] = tax.domain
            vals['amount'] = round(tax._compute_amount(price_base, 1.0),precision)
            vals['base'] = price_base
            taxes.append(vals)
        return taxes

    def _compute_fcp_icms(self, price_base):
        icms_fcp = self.filtered(lambda x: x.domain == 'fcp')
        vals_fcp = None
        if icms_fcp:
            vals_fcp = self._tax_vals(icms_fcp)

        if vals_fcp:
            fcp = icms_fcp._compute_amount(price_base, 1.0)
            vals_fcp['amount'] = fcp
            vals_fcp['base'] = price_base
            return [vals_fcp]
        else:
            return []

    def _compute_fcp_icms_st(self, price_base):
        icms_fcp_st = self.filtered(lambda x: x.domain == 'fcpst')
        vals_fcp = None
        if icms_fcp_st:
            vals_fcp = self._tax_vals(icms_fcp_st)

        if vals_fcp:
            fcp = icms_fcp_st._compute_amount(price_base, 1.0)
            vals_fcp['amount'] = fcp
            vals_fcp['base'] = price_base
            return [vals_fcp]
        else:
            return []

    def _compute_others(self, price_base):
        precision = self.env['decimal.precision'].precision_get('Account')
        others = self.filtered(lambda x: x.domain == 'outros' or not x.domain)
        if not others:
            return []
        vals = self._tax_vals(others)
        vals['domain'] = 'outros'
        vals['amount'] = round(others._compute_amount(price_base, 1.0),precision)
        vals['base'] = price_base
        return [vals]

    def sum_taxes(self, price_base, product=None, quantity=1.0, factor_uom=None, partner=None):
        ipi = self._compute_ipi(price_base)
        icms = self._compute_icms(
            price_base,
            ipi[0]['amount'] if ipi else 0.0)

        uom_fator_imposto = None
        uom_imposto_id = None
        if product:
            uom_fator_imposto = product.uom_fator_imposto
            uom_imposto_id = product.uom_imposto_id

        
        icmsst = self._compute_icms_st(
            price_base,
            ipi[0]['amount'] if ipi else 0.0,
            icms[0]['amount'] if icms else 0.0,
            quantity,
            factor_uom,
            uom_fator_imposto,
            uom_imposto_id)
        
        fcp = []
        fcpst = []
        if "tem_difal" in self.env.context:
            tem_difal = self.env.context['tem_difal']
        else:
            tem_difal = True if partner and partner.indicador_ie_dest == '9' else False
             
        difal = self._compute_difal(price_base, ipi[0]['amount'] if ipi else 0.0,tem_difal)
         
        if not tem_difal:
            fcp = self._compute_fcp_icms(price_base)
            fcpst = self._compute_fcp_icms_st(
                icmsst[0]['base'] if icmsst else 0.0)

        taxes = icms + icmsst + difal + ipi + fcp + fcpst
        taxes += self._compute_pis_cofins(price_base)
        taxes += self._compute_issqn(price_base)
        taxes += self._compute_ii(price_base)
        taxes += self._compute_retention(price_base)
        return taxes

    @api.multi
    def compute_all(self, price_unit, currency=None, quantity=1.0,
                    product=None, partner=None, factor_uom=None, fisc_pos=None):

        precision = self.env['decimal.precision'].precision_get('Account')
        exists_br_tax = len(self.filtered(lambda x: x.domain)) > 0
        if not exists_br_tax:
            res = super(AccountTax, self).compute_all(
                price_unit, currency, quantity, product, partner)
            res['price_without_tax'] = round(price_unit * quantity, precision)
            return res

        price_base = price_unit * quantity
        taxes = self.sum_taxes(price_base, product, quantity, factor_uom, partner)
        total_included = total_excluded = price_base

        for tax in taxes:
            tax_id = self.filtered(lambda x: x.id == tax['id'])
            amount = tax['amount'] if bool(tax.get('amount',None)) else 0.0
            if not tax_id.price_include:
                total_included += round(amount, precision)

        # retorna o valor dos impostos que permitem utilização de crédito
        total_allow_credit = 0
        for tax in taxes:
            tax_id = self.filtered(lambda x: x.id == tax['id'])
            if tax_id.allow_credit_utilization:
                total_allow_credit += round(tax['amount'], 2)

        return {
            'taxes': sorted(taxes, key=lambda k: k['sequence']),
            'total_excluded': total_excluded,
            'total_included': total_included,
            'total_allow_credit': total_allow_credit,
            'base': price_base,
        }
