from odoo import api, fields, models
from .cst import CST_ICMS
from .cst import CSOSN_SIMPLES
from .cst import CST_IPI
from .cst import CST_PIS_COFINS

class AccountFiscalPositionTaxRule(models.Model):
    _name = 'account.fiscal.position.tax.rule'
    _description = """Regra de Taxas da Posição Fiscal"""
    _order = 'sequence'

    sequence = fields.Integer(string="Sequência")
    name = fields.Char(string="Descrição", size=100)
    domain = fields.Selection([('icms', 'ICMS'),
                               ('pis', 'PIS'),
                               ('cofins', 'COFINS'),
                               ('ipi', 'IPI'),
                               ('issqn', 'ISSQN'),
                               ('ii', 'II'),
                               ('csll', 'CSLL'),
                               ('irrf', 'IRRF'),
                               ('inss', 'INSS'),
                               ('outros', 'Outros')], string="Tipo")
    fiscal_position_id = fields.Many2one(
        'account.fiscal.position', string="Posição Fiscal")

    state_ids = fields.Many2many('res.country.state', string="Estado Destino",
                                 domain=[('country_id.code', '=', 'BR')])
    fiscal_category_ids = fields.Many2many(
        'br_account.fiscal.category', string="Categorias Fiscais")
    tipo_produto = fields.Selection([('product', 'Produto'),
                                     ('service', 'Serviço')],
                                    string="Tipo produto", default="product")

    service_analytic_ids = fields.Many2many(
        'account.analytic.account', string="Conta",
        relation="account_analytic_account_ret_tax_rule_service_relation")
    
    service_type_ids = fields.Many2many(
        'br_account.service.type', string="Tipos Serviço",
        relation="br_account_service_type_ret_tax_rule_service_relation")

    product_fiscal_classification_ids = fields.Many2many(
        'product.fiscal.classification', string="Classificação Fiscal",
        relation="account_fiscal_position_tax_rule_prod_fiscal_clas_relation")

    cst_icms = fields.Selection(CST_ICMS, string="CST ICMS")
    csosn_icms = fields.Selection(CSOSN_SIMPLES, string="CSOSN ICMS")
    icms_benef = fields.Many2one('br_account.beneficio.fiscal', string="Benficio Fiscal")
    cst_pis = fields.Selection(CST_PIS_COFINS, string="CST PIS")
    cst_cofins = fields.Selection(CST_PIS_COFINS, string="CST COFINS")
    cst_ipi = fields.Selection(CST_IPI, string="CST IPI")
    enq_ipi = fields.Many2one('br_account.enquadramento.ipi', string="Enquadramento IPI")
    cla_ipi = fields.Char(string="Clas.Enquadram.", size=5)
    cfop_id = fields.Many2one('br_account.cfop', string="CFOP")
    tax_id = fields.Many2one('account.tax', string="Imposto")
    tax_icms_st_id = fields.Many2one('account.tax', string="ICMS ST",
                                     domain=[('domain', '=', 'icmsst')])
    icms_aliquota_credito = fields.Float(string="% Crédito de ICMS",digits=(12,4))
    icms_aliquota_diferimento = fields.Float("% Diferimento",digits=(12,4))
    incluir_ipi_base = fields.Boolean(string="Incl. IPI na base ICMS")
    reducao_icms = fields.Float(string="Redução de base")
    reducao_aliquota_icms = fields.Float(string="% Redução aliquota",digits=(12,4))
    reducao_icms_st = fields.Float(string="Redução de base ST")
    reducao_ipi = fields.Float(string="Redução de base IPI")
    icms_aliquota_reducao_base = fields.Float(string="Aliquota Redução base",digits=(12,4))
    l10n_br_issqn_deduction = fields.Float(string="% Dedução de base ISSQN")
    aliquota_mva = fields.Float(string="Alíquota MVA",digits=(12,4))
    icms_st_aliquota_deducao = fields.Float(
        string="% ICMS Próprio", digits=(12,4),
        help="Alíquota interna ou interestadual aplicada \
         sobre o valor da operação para deduzir do ICMS ST - Para empresas \
         do Simples Nacional ou usado em casos onde existe apenas ST sem ICMS")
    tem_difal = fields.Boolean(string="Aplicar Difal?")
    tax_icms_inter_id = fields.Many2one(
        'account.tax', help="Alíquota utilizada na operação Interestadual",
        string="ICMS Inter", domain=[('domain', '=', 'icms_inter')])
    tax_icms_intra_id = fields.Many2one(
        'account.tax', help="Alíquota interna do produto no estado destino",
        string="ICMS Intra", domain=[('domain', '=', 'icms_intra')])
    tax_icms_fcp_id = fields.Many2one(
        'account.tax', string="% FCP", domain=[('domain', '=', 'fcp')])
    tax_icms_fcp_st_id = fields.Many2one(
        'account.tax', string=u"% FCP ST", domain=[('domain', '=', 'fcpst')])
    preco_pauta = fields.Float(string="Preço de Pauta")
    issqn_tipo = fields.Selection([('N', 'Normal'),
                                   ('R', 'Retida'),
                                   ('S', 'Substituta'),
                                   ('I', 'Isenta')],
                                  string='Tipo do ISSQN', default='N')

class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    journal_id = fields.Many2one(
        'account.journal', string="Diário Contábil",
        help="Diário Contábil a ser utilizado na fatura.", copy=True)
    account_id = fields.Many2one(
        'account.account', string="Conta Contábil",
        help="Conta Contábil a ser utilizada na fatura.", copy=True)
    fiscal_observation_ids = fields.Many2many(
        'br_account.fiscal.observation', string="Mensagens Doc. Eletrônico",
        copy=True)
    note = fields.Text('Observações')

    product_serie_id = fields.Many2one(
        'br_account.document.serie', string='Série Produto',
        domain="[('fiscal_document_id', '=', product_document_id)]", copy=True)
    product_document_id = fields.Many2one(
        'br_account.fiscal.document', string='Documento Produto', copy=True)

    service_serie_id = fields.Many2one(
        'br_account.document.serie', string='Série Serviço',
        domain="[('fiscal_document_id', '=', service_document_id)]",
        copy=True)
    service_document_id = fields.Many2one(
        'br_account.fiscal.document', string='Documento Serviço', copy=True)

    icms_tax_rule_ids = fields.One2many(
        'account.fiscal.position.tax.rule', 'fiscal_position_id',
        string="Regras ICMS", domain=[('domain', '=', 'icms')], copy=True)
    ipi_tax_rule_ids = fields.One2many(
        'account.fiscal.position.tax.rule', 'fiscal_position_id',
        string="Regras IPI", domain=[('domain', '=', 'ipi')], copy=True)
    pis_tax_rule_ids = fields.One2many(
        'account.fiscal.position.tax.rule', 'fiscal_position_id',
        string="Regras PIS", domain=[('domain', '=', 'pis')], copy=True)
    cofins_tax_rule_ids = fields.One2many(
        'account.fiscal.position.tax.rule', 'fiscal_position_id',
        string="Regras COFINS", domain=[('domain', '=', 'cofins')],
        copy=True)
    issqn_tax_rule_ids = fields.One2many(
        'account.fiscal.position.tax.rule', 'fiscal_position_id',
        string="Regras ISSQN", domain=[('domain', '=', 'issqn')], copy=True)
    ii_tax_rule_ids = fields.One2many(
        'account.fiscal.position.tax.rule', 'fiscal_position_id',
        string="Regras II", domain=[('domain', '=', 'ii')], copy=True)
    irrf_tax_rule_ids = fields.One2many(
        'account.fiscal.position.tax.rule', 'fiscal_position_id',
        string="Regras IRRF", domain=[('domain', '=', 'irrf')], copy=True)
    csll_tax_rule_ids = fields.One2many(
        'account.fiscal.position.tax.rule', 'fiscal_position_id',
        string="Regras CSLL", domain=[('domain', '=', 'csll')], copy=True)
    inss_tax_rule_ids = fields.One2many(
        'account.fiscal.position.tax.rule', 'fiscal_position_id',
        string="Regras INSS", domain=[('domain', '=', 'inss')], copy=True)
    outros_tax_rule_ids = fields.One2many(
        'account.fiscal.position.tax.rule', 'fiscal_position_id',
        string="Outras Retenções", domain=[('domain', '=', 'outros')])
    fiscal_type = fields.Selection([('saida', 'Saída'),
                                    ('entrada', 'Entrada')],
                                   string="Tipo da posição", copy=True)
    natureza = fields.Char(string='Natureza Operação',oldname='nat_operacao')

    @api.model
    def _get_fpos_by_region(self, country_id=False, state_id=False,
                            zipcode=False, vat_required=False):
        fpos = super(AccountFiscalPosition, self)._get_fpos_by_region(
            country_id=country_id, state_id=state_id, zipcode=zipcode,
            vat_required=vat_required)
        type_inv = self.env.context.get('type', False)
        supplier = self.env.context.get('search_default_supplier', False)
        customer = self.env.context.get('search_default_customer', False)
        if type_inv == 'in_invoice' or supplier:
            type_inv = 'entrada'
        elif type_inv == 'out_invoice' or customer:
            type_inv = 'saida'
        fpos = self.search([('auto_apply', '=', True),
                            ('fiscal_type', '=', type_inv)], limit=1)
        return fpos

    @api.model
    def map_tax_extra_values(self, product, partner, fiscal_classification, service_type, issqn_tipo, analytic):
        to_state = partner.state_id
        to_fiscal_type = product.fiscal_type
        to_fiscal_category = product.fiscal_category_id
        to_fiscal_classification = fiscal_classification if bool(fiscal_classification) else product.fiscal_classification_id
        to_service_type = service_type if bool(service_type) else product.service_type_id

        taxes = ('icms', 'simples', 'ipi', 'pis', 'cofins',
                 'issqn', 'ii', 'irrf', 'csll', 'inss', 'outros')
        res = {}
        for tax in taxes:
            vals = self._filter_rules(self.id, tax, to_fiscal_type, to_fiscal_category, 
                                      to_fiscal_classification, to_service_type, issqn_tipo, to_state, analytic)
            res.update({k: v for k, v in vals.items() if v})
        return res

    def _filter_rules(self, fpos_id, type_tax, fiscal_type, fiscal_category, fiscal_classification, service_type, issqn_tipo, state, analytic):
        rule_obj = self.env['account.fiscal.position.tax.rule']
        domain = [('fiscal_position_id', '=', fpos_id),
                  ('domain', '=', type_tax)]
        rules = rule_obj.search(domain)
        if rules:
            rules_points = {}
            for rule in rules:

                # Calcula a pontuacao da regra.
                # Quanto mais alto, mais adequada está a regra em relacao ao
                # faturamento
                rules_points[rule.id] = self._calculate_points(
                    rule, fiscal_type, fiscal_category, fiscal_classification, service_type, issqn_tipo, state, analytic)

            # Calcula o maior valor para os resultados obtidos
            greater_rule = max([(v, k) for k, v in rules_points.items()])
            # Se o valor da regra for menor do que 0, a regra é descartada.
            if greater_rule[0] < 0:
                return {}

            # Procura pela regra associada ao id -> (greater_rule[1])
            rules = [rules.browse(greater_rule[1])]

            # Retorna dicionario com o valores dos campos de acordo com a regra
            return {
                ('%s_rule_id' % type_tax): rules[0],
                'cfop_id': rules[0].cfop_id,
                'icms_benef': rules[0].icms_benef,
                ('tax_%s_id' % type_tax): rules[0].tax_id,
                # ICMS
                'icms_cst_normal': rules[0].cst_icms,
                'icms_aliquota_reducao_base': rules[0].reducao_icms,
                'incluir_ipi_base': rules[0].incluir_ipi_base,
                # ICMS Dif
                'icms_aliquota_diferimento': rules[0].icms_aliquota_diferimento,
                # ICMS ST
                'tax_icms_st_id': rules[0].tax_icms_st_id,
                'icms_st_aliquota_mva': rules[0].aliquota_mva,
                'icms_st_aliquota_reducao_base': rules[0].reducao_icms_st,
                'icms_st_aliquota_deducao': rules[0].icms_st_aliquota_deducao,
                'tax_icms_fcp_st_id': rules[0].tax_icms_fcp_st_id,
                'icms_st_preco_pauta': rules[0].preco_pauta,
                # ICMS Difal
                'tem_difal': rules[0].tem_difal,
                'tax_icms_inter_id': rules[0].tax_icms_inter_id,
                'tax_icms_intra_id': rules[0].tax_icms_intra_id,
                'tax_icms_fcp_id': rules[0].tax_icms_fcp_id,
                # Simples
                'icms_csosn_simples': rules[0].csosn_icms,
                'icms_aliquota_credito': rules[0].icms_aliquota_credito,
                # IPI
                'ipi_cst': rules[0].cst_ipi,
                'ipi_reducao_bc': rules[0].reducao_ipi,
                'ipi_codigo_enquadramento': rules[0].enq_ipi,
                'ipi_classe_enquadramento': rules[0].cla_ipi,
                # PIS
                'pis_cst': rules[0].cst_pis,
                # PIS
                'cofins_cst': rules[0].cst_cofins,
                # ISSQN
                'l10n_br_issqn_deduction': rules[0].l10n_br_issqn_deduction,
            }
        else:
            return{}

    def _calculate_points(self, rule, fiscal_type, fiscal_category, fiscal_classification, service_type, issqn_tipo, state, analytic):
        """Calcula a pontuação das regras. A pontuação aumenta de acordo
        com os 'matches'. Não havendo match(exceto quando o campo não está
        definido) retorna o valor -1, que posteriormente será tratado como
        uma regra a ser descartada.
        """

        rule_points = 0

        # Verifica o tipo do produto. Se sim, avança para calculo da pontuação
        # Se não, retorna o valor -1 (a regra será descartada)
        if fiscal_type == rule.tipo_produto:

            # Verifica a categoria fiscal. Se contido, adiciona 1 ponto
            # Se não, retorna valor -1 (a regra será descartada)
            if fiscal_category in rule.fiscal_category_ids:
                rule_points += 1
            elif len(rule.fiscal_category_ids) > 0:
                return -1

            if fiscal_type == 'product':
                # Verifica produtos. Se contido, adiciona 1 ponto
                # Se não, retorna -1
                if fiscal_classification in rule.product_fiscal_classification_ids:
                    rule_points += 1
                elif len(rule.product_fiscal_classification_ids) > 0:
                    return -1
    
                # Verifica o estado. Se contido, adiciona 1 ponto
                # Se não, retorna -1
                if state in rule.state_ids:
                    rule_points += 1
                elif len(rule.state_ids) > 0:
                    return -1

            if fiscal_type == 'service':
                if  issqn_tipo == rule.issqn_tipo:
                    rule_points += 1
                elif bool(rule.issqn_tipo):
                    return -1
                
                if analytic in rule.service_analytic_ids:
                    rule_points += 1
                elif len(rule.service_analytic_ids) > 0:
                    return -1
                
                if service_type in rule.service_type_ids:
                    rule_points += 1
                elif len(rule.service_type_ids) > 0:
                    return -1
        else:
            return -1

        return rule_points
