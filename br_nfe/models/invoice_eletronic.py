# © 2016 Danimar Ribeiro <danimaribeiro@gmail.com>, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re
import io
import pytz
import time
import base64
import logging
import hashlib
from lxml import etree
from datetime import datetime, timezone, timedelta
from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT
from odoo.addons import decimal_precision as dp
from calendar import monthrange

_logger = logging.getLogger(__name__)

try:
    from pytrustnfe.nfe import autorizar_nfe
    from pytrustnfe.nfe import xml_autorizar_nfe
    from pytrustnfe.nfe import retorno_autorizar_nfe
    from pytrustnfe.nfe import recepcao_evento_cancelamento
    from pytrustnfe.nfe import consultar_protocolo_nfe
    from pytrustnfe.nfe import nfe_status_servico
    from pytrustnfe.certificado import Certificado
    from pytrustnfe.utils import ChaveNFe, gerar_chave, gerar_nfeproc, \
        gerar_nfeproc_cancel
    from pytrustnfe.nfe.danfe import danfe
    from pytrustnfe.xml.validate import valida_nfe
#    from pytrustnfe.urls import url_qrcode, url_qrcode_exibicao
except ImportError:
    _logger.error('Cannot import pytrustnfe', exc_info=True)

STATE = {'edit': [('readonly', False)]}


class InvoiceEletronic(models.Model):
    _inherit = 'invoice.eletronic'

    @api.multi
    @api.depends('chave_nfe')
    def _compute_format_danfe_key(self):
        for item in self:
            item.chave_nfe_danfe = re.sub("(.{4})", "\\1.",
                                          item.chave_nfe, 10, re.DOTALL)

    @api.multi
    def generate_correction_letter(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "wizard.carta.correcao.eletronica",
            "views": [[False, "form"]],
            "name": _("Carta de Correção"),
            "target": "new",
            "context": {'default_eletronic_doc_id': self.id},
        }

    payment_mode_id = fields.Many2one(
        'l10n_br.payment.mode', string='Modo de Pagamento',
        readonly=True, states=STATE)
    state = fields.Selection(selection_add=[('denied', 'Denegado')])
    iest = fields.Char(string="IE Subst. Tributário")
    ambiente_nfe = fields.Selection(
        string="Ambiente NFe", related="company_id.tipo_ambiente",
        readonly=True)
    ind_final = fields.Selection([
        ('0', 'Não'),
        ('1', 'Sim')
    ], 'Consumidor Final', readonly=True, states=STATE, required=False,
        help='Indica operação com Consumidor final.', default='0')
    ind_pres = fields.Selection([
        ('0', 'Não se aplica'),
        ('1', 'Operação presencial'),
        ('2', 'Operação não presencial, pela Internet'),
        ('3', 'Operação não presencial, Teleatendimento'),
        ('4', 'NFC-e em operação com entrega em domicílio'),
        ('5', 'Operação presencial, fora do estabelecimento'),
        ('9', 'Operação não presencial, outros'),
    ], 'Indicador de Presença', readonly=True, states=STATE, required=False,
        help='Indicador de presença do comprador no\n'
             'estabelecimento comercial no momento\n'
             'da operação.', default='0')
    ind_dest = fields.Selection([
        ('1', '1 - Operação Interna'),
        ('2', '2 - Operação Interestadual'),
        ('3', '3 - Operação com exterior')],
        string="Indicador Destinatário", readonly=True, states=STATE)
    ind_ie_dest = fields.Selection([
        ('1', '1 - Contribuinte ICMS'),
        ('2', '2 - Contribuinte Isento de Cadastro'),
        ('9', '9 - Não Contribuinte')],
        string="Indicador IE Dest.", help="Indicador da IE do desinatário",
        readonly=True, states=STATE)
    tipo_emissao = fields.Selection([
        ('1', '1 - Emissão normal'),
        ('2', '2 - Contingência FS-IA, com impressão do DANFE em formulário \
         de segurança'),
        ('3', '3 - Contingência SCAN'),
        ('4', '4 - Contingência DPEC'),
        ('5', '5 - Contingência FS-DA, com impressão do DANFE em \
         formulário de segurança'),
        ('6', '6 - Contingência SVC-AN'),
        ('7', '7 - Contingência SVC-RS'),
        ('9', '9 - Contingência off-line da NFC-e')],
        string="Tipo de Emissão", readonly=True, states=STATE, default='1')
    data_contingencia = fields.Datetime(
        string='Data Contingência',
        readonly=True,
        states=STATE)
    justificativa_contingencia = fields.Char(
        string='Motivo da Contingência', states=STATE)

    # Transporte
    data_entrada_saida = fields.Datetime(
        string="Data Entrega", help="Data para saída/entrada das mercadorias")
    modalidade_frete = fields.Selection(
        [('0', '0 - Contratação do Frete por conta do Remetente (CIF)'),
         ('1', '1 - Contratação do Frete por conta do Destinatário (FOB)'),
         ('2', '2 - Contratação do Frete por conta de Terceiros'),
         ('3', '3 - Transporte Próprio por conta do Remetente'),
         ('4', '4 - Transporte Próprio por conta do Destinatário'),
         ('9', '9 - Sem Ocorrência de Transporte')],
        string='Modalidade do frete', default="9",
        readonly=True, states=STATE)
    transportadora_id = fields.Many2one(
        'res.partner', string="Transportadora", readonly=True, states=STATE)
    placa_veiculo = fields.Char(
        string='Placa do Veículo', size=7, readonly=True, states=STATE)
    uf_veiculo = fields.Char(
        string='UF da Placa', size=2, readonly=True, states=STATE)
    rntc = fields.Char(
        string="RNTC", size=20, readonly=True, states=STATE,
        help="Registro Nacional de Transportador de Carga")

    reboque_ids = fields.One2many(
        'nfe.reboque', 'invoice_eletronic_id',
        string="Reboques", readonly=True, states=STATE)
    volume_ids = fields.One2many(
        'nfe.volume', 'invoice_eletronic_id',
        string="Volumes", readonly=True, states=STATE)

    # Exportação
    uf_saida_pais_id = fields.Many2one(
        'res.country.state', domain=[('country_id.code', '=', 'BR')],
        string="UF Saída do País", readonly=True, states=STATE)
    local_embarque = fields.Char(
        string='Local de Embarque', size=60, readonly=True, states=STATE)
    local_despacho = fields.Char(
        string='Local de Despacho', size=60, readonly=True, states=STATE)

    # Grupo de exportação
#     number_draw = fields.Char(
#         string='Nº concessório de Drawback', size=11, compute='_get_export_group',
#         help="O número do Ato Concessório de Suspensão deve ser preenchido com 11 dígitos (AAAANNNNNND)"
#         "e o número do Ato Concessório de Drawback Isenção deve ser preenchido com 9 dígitos (AANNNNNND)."
#         "(Observação incluída na NT 2013/005 v. 1.10)")
#     number_reg = fields.Char(
#         string='Nº Registro de Exportação', size=12)
#     key_nfe = fields.Char(
#         string='Chave de Acesso da NF-e rec. p/ exportação', size=44,
#         help="NF-e recebida com fim específico de exportação. No caso de operação com CFOP 3.503,"
#         "informar a chave de acesso da NF-e que efetivou a exportação")
#     qty_export = fields.Float(
#         string='Quant. do item realmente exportado', digits=dp.get_precision('Product Unit of Measure'))
# 
#     import_export_group_ids = fields.One2many(
#         'account.export.group',
#         'invoice_eletronic_line_id', 'Grupo de Exportação')

    # Cobrança
    numero_fatura = fields.Char(
        string="Fatura", readonly=True, states=STATE)
    fatura_bruto = fields.Float(
        string="Valor Original", readonly=True, states=STATE)
    fatura_desconto = fields.Float(
        string="Desconto", readonly=True, states=STATE)
    fatura_liquido = fields.Float(
        string="Valor Líquido", readonly=True, states=STATE)

    duplicata_ids = fields.One2many(
        'nfe.duplicata', 'invoice_eletronic_id',
        string="Duplicatas", readonly=True, states=STATE)

    pagamento_ids = fields.One2many(
        'nfe.pagamento', 'invoice_eletronic_id',
        string="Pagamentos", readonly=True, states=STATE)

    # Compras
    nota_empenho = fields.Char(
        string="Nota de Empenho", size=22, readonly=True, states=STATE)
    pedido_compra = fields.Char(
        string="Pedido Compra", size=60, readonly=True, states=STATE)
    contrato_compra = fields.Char(
        string="Contrato Compra", size=60, readonly=True, states=STATE)

    sequencial_evento = fields.Integer(
        string="Sequêncial Evento", default=1, readonly=True, states=STATE)
    recibo_nfe = fields.Char(
        string="Recibo NFe", size=50, readonly=True, states=STATE)
    chave_nfe = fields.Char(
        string="Chave NFe", size=50, readonly=True, states=STATE)
    chave_nfe_danfe = fields.Char(
        string="Chave Formatado", compute="_compute_format_danfe_key")
    protocolo_nfe = fields.Char(
        string="Protocolo", size=50, readonly=True, states=STATE,
        help="Protocolo de autorização da NFe")
    nfe_processada = fields.Binary(string="Xml da NFe", readonly=True)
    nfe_processada_name = fields.Char(
        string="Xml da NFe", size=100, readonly=True)

    valor_icms_uf_remet = fields.Float(
        string="ICMS Remetente", readonly=True, states=STATE,
        help='Valor total do ICMS Interestadual para a UF do Remetente')
    valor_icms_uf_dest = fields.Float(
        string="ICMS Destino", readonly=True, states=STATE,
        help='Valor total do ICMS Interestadual para a UF de destino')
    valor_icms_fcp_uf_dest = fields.Float(
        string="Total ICMS FCP", readonly=True, states=STATE,
        help='Total total do ICMS relativo Fundo de Combate à Pobreza (FCP) \
        da UF de destino')

    # NFC-e
    qrcode_hash = fields.Char(string='QR-Code hash')
    qrcode_url = fields.Char(string='QR-Code URL')
    metodo_pagamento = fields.Selection(
        [('01', 'Dinheiro'),
         ('02', 'Cheque'),
         ('03', 'Cartão de Crédito'),
         ('04', 'Cartão de Débito'),
         ('05', 'Crédito Loja'),
         ('10', 'Vale Alimentação'),
         ('11', 'Vale Refeição'),
         ('12', 'Vale Presente'),
         ('13', 'Vale Combustível'),
         ('14', 'Duplicata Mercantil'),
         ('15', 'Boleto Bancário'),
         ('90', 'Sem pagamento'),
         ('99', 'Outros')],
        string="Forma de Pagamento", default="01")
    valor_pago = fields.Float(string='Valor pago')
    troco = fields.Float(string='Troco')

    # Documentos Relacionados
    fiscal_document_related_ids = fields.One2many(
        'br_account.document.related', 'invoice_eletronic_id',
        'Documentos Fiscais Relacionados', readonly=True, states=STATE)

    # CARTA DE CORRECAO
    cartas_correcao_ids = fields.One2many(
        'carta.correcao.eletronica.evento', 'eletronic_doc_id',
        string="Cartas de Correção", readonly=True, states=STATE)

    def can_unlink(self):
        res = super(InvoiceEletronic, self).can_unlink()
        if self.state == 'denied':
            return False
        return res

    @api.multi
    def unlink(self):
        for item in self:
            if item.state in ('denied'):
                raise UserError(
                    _('Documento Eletrônico Denegado - Proibido excluir'))
        super(InvoiceEletronic, self).unlink()

    @api.multi
    def _hook_validation(self):
        errors = super(InvoiceEletronic, self)._hook_validation()
        if self.model in ('55', '65'):
            if not self.company_id.partner_id.inscr_est:
                errors.append('Emitente / Inscrição Estadual')
            for eletr in self.eletronic_item_ids:
                prod = "Produto: {} - {}".format(eletr.product_id.default_code or '',eletr.product_id.name or '')
                if not eletr.cfop:
                    errors.append('{} - CFOP'.format(prod))
                if eletr.tipo_produto == 'product':
                    if not bool(eletr.ncm):
                        errors.append('{} - Sem o código NCM'.format(prod))
                    else:
                        ncm = re.sub('[^0-9]', '', eletr.ncm or '00')
                        if len(ncm) != 8 and len(ncm) != 2:
                            errors.append('{} - NCM {} - Código do NCM deve conter 2 ou 8 digitos'.format(prod,eletr.ncm or ''))
                    if not eletr.icms_cst:
                        errors.append('{} - CST do ICMS'.format(prod))
                    if not eletr.ipi_cst:
                        errors.append('{} - CST do IPI'.format(prod))
                    if not bool(eletr.uom_id):
                        errors.append('{} - Unidade de Medida'.format(prod))
                if eletr.tipo_produto == 'service':
                    if not eletr.issqn_codigo:
                        errors.append('{} - Código de Serviço'.format(prod))
                if not eletr.pis_cst:
                    errors.append('{} - CST do PIS'.format(prod))
                if not eletr.cofins_cst:
                    errors.append('{} - CST do Cofins'.format(prod))
        # NF-e
        if self.model == '55':
            if not self.fiscal_position_id:
                errors.append('Configure a posição fiscal')
            if self.company_id.accountant_id and not \
               self.company_id.accountant_id.cnpj_cpf:
                errors.append('Emitente / CNPJ do escritório contabilidade')
        # NFC-e
        if self.model == '65':
            if len(self.company_id.id_token_csc or '') != 6:
                errors.append("Identificador do CSC inválido")
            if not len(self.company_id.csc or ''):
                errors.append("CSC Inválido")
            if self.partner_id.cnpj_cpf is None:
                errors.append("CNPJ/CPF do Parceiro inválido")
            if len(self.serie) == 0:
                errors.append("Número de Série da NFe Inválido")

        return errors

    def _prepare_eletronic_invoice_item_rastros(self, item, einvoice):
        rastros = []
        # Desabilitado essas verificações, pois estava gerando
        # duplicação de lotes em pedidos agrupados
        # pickings = []
        # type_order = einvoice.invoice_id.type
        # if 'picking_ids' in self.env['account.invoice']._fields:
        #     pickings = einvoice.invoice_id.picking_ids
        # else:
        #     Essa condição do else em meus testes gerando vários tipos
        #     de notas, nunca chegou a passar. Pois quando não há picking
        #     o tratamento é feito antes de chegar neste método
        #     model = 'sale.order' if type_order in \
        #     ('out_invoice', 'in_invoice', 'in_refund', 'out_refund') \
        #        else 'purchase.order'
        #     orders = self.env[model].list_orders_by_invoice(
        #        einvoice.invoice_id)
        #     for order in orders:
        #         pickings.append(order.picking_ids)
        # for picking in pickings:
        #     picking_type = picking.picking_type_id
        # if picking_type.use_create_lots or picking_type.use_existing_lots:
        move_ids = 'move_ids' in item.env['account.invoice.line']._fields

        if not item.account_invoice_line_id or not move_ids:
            return rastros

        # Aqui é necessário ter a segunda opção,
        # pois a primeira traz os pedidos agrupados
        # e a segunda traz o move_ids de uma nota de crédito de compra.
        moves = self.env['account.invoice'].get_stock_move(
            item.account_invoice_line_id) or item.account_invoice_line_id.move_ids

        if not moves:
            return
        for movs in moves:
            mov = movs.move_line_ids.filtered(
                lambda line: line.lot_id.id is not False)
        for move in mov:
            dt_fab_obj = datetime.strptime(move.create_date, DATETIME_FORMAT)
            dt_val = move.lot_id.life_date if move.lot_id.life_date else \
                str(dt_fab_obj.year) + '-' + str(dt_fab_obj.month) + '-' + \
                str(monthrange(dt_fab_obj.year, dt_fab_obj.month)
                    [1]) + ' 00:00:00'
            dt_val_obj = datetime.strptime(dt_val, DATETIME_FORMAT)
            num_lot = move.lot_id.name
            qtd_lot = move.qty_done
            rastros.append({
                'nLote': num_lot,
                'qLote': "%.03f" % qtd_lot,
                'dFab': dt_fab_obj.date().strftime('%Y-%m-%d'),
                'dVal': dt_val_obj.date().strftime('%Y-%m-%d'),
            })

        return rastros

    @api.multi
    def _prepare_eletronic_invoice_item(self, item, invoice):
        res = super(InvoiceEletronic, self)._prepare_eletronic_invoice_item(
            item, invoice)
        if self.model not in ('55', '65'):
            return res

        if self.ambiente != 'homologacao':
            if item.name == item.product_id.name_get()[0][1]:
                xProd = item.product_id.with_context(display_default_code=False).name_get()[0][1]
            else:
                xProd = item.name
        else:
            xProd = 'NOTA FISCAL EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL'

        price_precis = dp.get_precision('Product Price')(self.env.cr)
        qty_precis = dp.get_precision('Product Unit of Measure')(self.env.cr)
        qty_frmt = '{:.%sf}' % qty_precis[1] if qty_precis[1] <= 4 else '{:.4f}'
        price_frmt = '{:.%sf}' % price_precis[1] if price_precis[1] <= 4 else '{:.4f}'
        prod = {
            'cProd': item.code,
            'cEAN': item.product_id.barcode or 'SEM GTIN',
            'xProd': xProd,
            'NCM': re.sub('[^0-9]', '', item.ncm or '00')[:8],
            'CFOP': item.cfop,
            'uCom': '{:.6}'.format(item.uom_id.name or ''),
            'qCom': qty_frmt.format(item.quantidade),
            'vUnCom': price_frmt.format(item.preco_unitario),
            'vProd':  "%.02f" % item.valor_bruto,
            'cEANTrib': item.product_id.barcode or 'SEM GTIN',
            'uTrib': '{:.6}'.format(item.uom_id.name or ''),
            'qTrib': qty_frmt.format(item.quantidade),
            'vUnTrib': price_frmt.format(item.preco_unitario),
            'vFrete': "%.02f" % item.frete if item.frete else '',
            'vSeg': "%.02f" % item.seguro if item.seguro else '',
            'vDesc': "%.02f" % item.desconto if item.desconto else '',
            'vOutro': "%.02f" % item.outras_despesas if item.outras_despesas else '',
            'indTot': item.indicador_total,
            'cfop': item.cfop,
            'CEST': re.sub('[^0-9]', '', item.cest or ''),
            'nItemPed': item.item_pedido_compra if item.item_pedido_compra else '',
            'xPed': item.nr_pedido_compra if item.nr_pedido_compra else '', 
        }
        if item.icms_benef:
            prod['cBenef'] = item.icms_benef.code
            
        di_vals = []
        for di in item.import_declaration_ids:
            adicoes = []
            for adi in di.line_ids:
                adicoes.append({
                    'nAdicao': str(int(adi.name)),
                    'nSeqAdic': str(int(adi.sequence_addition)),
                    'cFabricante': adi.manufacturer_code,
                    'vDescDI': "%.02f" % adi.amount_discount
                    if adi.amount_discount else '',
                    'nDraw': adi.drawback_number or '',
                })

            dt_registration = datetime.strptime(
                di.date_registration, DATE_FORMAT)
            dt_release = datetime.strptime(di.date_release, DATE_FORMAT)
            di_vals.append({
                'nDI': di.name,
                'dDI': dt_registration.strftime('%Y-%m-%d'),
                'xLocDesemb': di.location,
                'UFDesemb': di.state_id.code,
                'dDesemb': dt_release.strftime('%Y-%m-%d'),
                'tpViaTransp': di.type_transportation,
                'vAFRMM': "%.02f" % di.afrmm_value if di.afrmm_value else '',
                'tpIntermedio': di.type_import,
                'CNPJ': di.thirdparty_cnpj or '',
                'UFTerceiro': di.thirdparty_state_id.code or '',
                'cExportador': di.exporting_code,
                'adi': adicoes,
            })

        prod["DI"] = di_vals

        #prod["rastro"] = self._prepare_eletronic_invoice_item_rastros(item, invoice)


        imposto = {
            'vTotTrib': "%.02f" % item.tributos_estimados,
            'PIS': {
                'CST': item.pis_cst,
                'vBC': "%.02f" % item.pis_base_calculo,
                'pPIS': "%.04f" % item.pis_aliquota,
                'vPIS': "%.02f" % item.pis_valor
            },
            'COFINS': {
                'CST': item.cofins_cst,
                'vBC': "%.02f" % item.cofins_base_calculo,
                'pCOFINS': "%.04f" % item.cofins_aliquota,
                'vCOFINS': "%.02f" % item.cofins_valor
            },
        }
        if len(item.import_declaration_ids) > 0:
            imposto.update({        
                'II': {
                    'vBC': "%.02f" % item.ii_base_calculo,
                    'vDespAdu': "%.02f" % item.ii_valor_despesas,
                    'vII': "%.02f" % item.ii_valor,
                    'vIOF': "%.02f" % item.ii_valor_iof
                }
            })

        if item.tipo_produto == 'service':
            retencoes = item.pis_valor_retencao + \
                item.cofins_valor_retencao + item.inss_valor_retencao + \
                item.irrf_valor_retencao + item.csll_valor_retencao
            imposto.update({
                'ISSQN': {
                    'vBC': "%.02f" % item.issqn_base_calculo,
                    'vAliq': "%.02f" % item.issqn_aliquota,
                    'vISSQN': "%.02f" % item.issqn_valor,
                    'cMunFG': "%s%s" % (invoice.company_id.state_id.ibge_code,
                                        invoice.company_id.city_id.ibge_code),
                    'cListServ': item.issqn_codigo,
                    'vDeducao': '',
                    'vOutro': "%.02f" % retencoes if retencoes else '',
                    'vISSRet': "%.02f" % item.issqn_valor_retencao
                    if item.issqn_valor_retencao else '',
                    'indISS': 1,  # Exigivel
                    'cServico': item.issqn_codigo,
                    'cMun': "%s%s" % (invoice.company_id.state_id.ibge_code,
                                      invoice.company_id.city_id.ibge_code),
                    'indIncentivo': 2,  # Não
                }
            })
        else:
            imposto.update({
                'ICMS': {
                    'orig':  item.origem,
                    'CST': item.icms_cst,
                    'modBC': item.icms_tipo_base,
                    'pRedBC': "%.04f" % item.icms_aliquota_reducao_base,
                    'vBC': "%.02f" % item.icms_base_calculo,
                    'pICMS': "%.04f" % item.icms_aliquota,
                    'vICMSOp': "%.02f" % item.icms_valor_operacao,
                    'pDif': "%.04f" % item.icms_aliquota_diferimento,
                    'vICMSDif': "%.02f" % item.icms_valor_diferido,
                    'vICMS': "%.02f" % item.icms_valor,
                    'modBCST': item.icms_st_tipo_base,
                    'pMVAST': "%.04f" % item.icms_st_aliquota_mva if item.icms_st_tipo_base == '4' else '',
                    'pRedBCST': "%.04f" % item.icms_st_aliquota_reducao_base,
                    'vBCST': "%.02f" % item.icms_st_base_calculo,
                    'pICMSST': "%.04f" % item.icms_st_aliquota,
                    'vICMSST': "%.02f" % item.icms_st_valor,
                    'pCredSN': "%.04f" % item.icms_aliquota_credito,
                    'vCredICMSSN': "%.02f" % item.icms_valor_credito,
                    'vBCFCP': "%.02f" % item.icms_base_calculo_fcp if not item.tem_difal and item.icms_base_calculo_fcp > 0 else '',
                    'pFCP': "%.02f" % item.icms_aliquota_fcp if not item.tem_difal and item.icms_aliquota_fcp > 0 else '',
                    'vFCP': "%.02f" % item.icms_fcp if not item.tem_difal and item.icms_fcp > 0 else '',
                    'vBCFCPST': "%.02f" % item.icms_base_calculo_fcp_st if item.icms_base_calculo_fcp_st > 0 else '',
                    'pFCPST': "%.02f" % item.icms_aliquota_fcp_st if item.icms_aliquota_fcp_st > 0 else '',
                    'vFCPST': "%.02f" % item.icms_fcp_st if item.icms_fcp_st > 0 else '',
                    'vICMSSubstituto': "%.02f" % item.icms_substituto,
                    'vBCSTRet': "%.02f" % item.icms_bc_st_retido,
                    'pST': "%.04f" % item.icms_aliquota_st_retido,
                    'vICMSSTRet': "%.02f" % item.icms_st_retido,
                },
                'IPI': {
                    'clEnq': item.ipi_classe_enquadramento or '',
                    'cEnq': item.ipi_codigo_enquadramento.code or '999',
                    'CST': item.ipi_cst,
                    'vBC': "%.02f" % item.ipi_base_calculo,
                    'pIPI': "%.04f" % item.ipi_aliquota,
                    'vIPI': "%.02f" % item.ipi_valor
                },
            })
        if item.tem_difal:
            imposto['ICMSUFDest'] = {
                'vBCUFDest': "%.02f" % item.icms_bc_uf_dest,
                'pFCPUFDest': "%.02f" % item.icms_aliquota_fcp_uf_dest,
                'pICMSUFDest': "%.02f" % item.icms_aliquota_uf_dest,
                'pICMSInter': "%.02f" % item.icms_aliquota_interestadual,
                'pICMSInterPart': "%.02f" % item.icms_aliquota_inter_part,
                'vBCFCPUFDest': "%.02f" % item.icms_bc_uf_dest,
                'vFCPUFDest': "%.02f" % item.icms_fcp_uf_dest,
                'vICMSUFDest': "%.02f" % item.icms_uf_dest,
                'vICMSUFRemet': "%.02f" % item.icms_uf_remet, }
            
        return {
            'prod': prod, 
            'imposto': imposto, 
            'infAdProd': item.informacao_adicional.replace('\n', '<br />') if bool(item.informacao_adicional) else '',
        }

    @api.multi
    def _prepare_eletronic_invoice_values(self):
        res = super(InvoiceEletronic, self)._prepare_eletronic_invoice_values()
        if self.model not in ('55', '65'):
            return res

        tz = pytz.timezone(self.env.user.tz)
        dt_emissao = datetime.now(tz).replace(microsecond=0).isoformat()
        
        if self.model == '65':
            default_method = self.company_id.nfce_contingencia
            ws_status = self.query_status_webservice(response_type='json')
            if ws_status.cStat != 107 or default_method:
                self.tipo_emissao = '9'
        
        dt_saida = fields.Datetime.from_string(self.data_entrada_saida)
        if dt_saida:
            dt_saida = tz.localize(dt_saida).replace(microsecond=0).isoformat()
        else:
            dt_saida = dt_emissao
        paramObj = self.env['ir.config_parameter']
        ide = {
            'cUF': self.company_id.state_id.ibge_code,
            'cNF': "%08d" % self.numero_controle,
            'natOp': self.fiscal_position_id.natureza,
            'mod': self.model,
            'serie': self.serie.code,
            'nNF': self.numero,
            'dhEmi': dt_emissao,
            'dhSaiEnt': dt_saida,
            'tpNF': '0' if self.tipo_operacao == 'entrada' else '1',
            'idDest': self.ind_dest or 1,
            'cMunFG': "%s%s" % (self.company_id.state_id.ibge_code,
                                self.company_id.city_id.ibge_code),
            # Formato de Impressão do DANFE - 1 - Danfe Retrato, 4 - Danfe NFCe
            'tpImp': '1' if self.model == '55' else '4',
            'tpEmis': int(self.tipo_emissao),
            'tpAmb': 2 if self.ambiente == 'homologacao' else 1,
            'finNFe': self.finalidade_emissao,
            'indFinal': self.ind_final or '1',
            'indPres': self.ind_pres or '1',
            'procEmi': 0,
            'softEmi': paramObj.sudo().get_param('NFe.softEmi'),
        }

        if self.tipo_emissao == '9':
            self.data_contingencia = self.data_emissao
            if self.justificativa_contingencia:
                justificativa = self.justificativa_contingencia
            else:
                justificativa = 'FALHA NA COMUNICACAO COM WEBSERVICE'
            ide.update({
                'dhCont': dt_emissao,
                'xJust': justificativa,
            })

        # Documentos Relacionados
        documentos = []
        for doc in self.fiscal_document_related_ids:
            data = fields.Datetime.from_string(doc.date)
            if doc.document_type == 'nfe':
                documentos.append({
                    'refNFe': doc.access_key
                })
            elif doc.document_type == 'nf':
                documentos.append({
                    'refNF': {
                        'cUF': doc.state_id.ibge_code,
                        'AAMM': data.strftime("%y%m"),
                        'CNPJ': re.sub('[^0-9]', '', doc.cnpj_cpf),
                        'mod': doc.fiscal_document_id.code,
                        'serie': doc.serie,
                        'nNF': doc.internal_number,
                    }
                })

            elif doc.document_type == 'cte':
                documentos.append({
                    'refCTe': doc.access_key
                })
            elif doc.document_type == 'nfrural':
                cnpj_cpf = re.sub('[^0-9]', '', doc.cnpj_cpf)
                documentos.append({
                    'refNFP': {
                        'cUF': doc.state_id.ibge_code,
                        'AAMM': data.strftime("%y%m"),
                        'CNPJ': cnpj_cpf if len(cnpj_cpf) == 14 else '',
                        'CPF': cnpj_cpf if len(cnpj_cpf) == 11 else '',
                        'IE': doc.inscr_est,
                        'mod': doc.fiscal_document_id.code,
                        'serie': doc.serie,
                        'nNF': doc.internal_number,
                    }
                })
            elif doc.document_type == 'cf':
                documentos.append({
                    'refECF': {
                        'mod': doc.fiscal_document_id.code,
                        'nECF': doc.serie,
                        'nCOO': doc.internal_number,
                    }
                })

        ide['NFref'] = documentos
        emit = {
            'tipo': self.company_id.partner_id.company_type,
            'cnpj_cpf': re.sub('[^0-9]', '', self.company_id.cnpj_cpf),
            'xNome': self.company_id.legal_name,
            'xFant': self.company_id.name,
            'enderEmit': {
                'xLgr': self.company_id.street,
                'nro': self.company_id.number,
                'xCpl': self.company_id.street2 or '',
                'xBairro': self.company_id.district,
                'cMun': '%s%s' % (
                    self.company_id.partner_id.state_id.ibge_code,
                    self.company_id.partner_id.city_id.ibge_code),
                'xMun': self.company_id.city_id.name,
                'UF': self.company_id.state_id.code,
                'CEP': re.sub('[^0-9]', '', self.company_id.zip),
                'cPais': self.company_id.country_id.ibge_code,
                'xPais': self.company_id.country_id.name,
                'fone': re.sub('[^0-9]', '', self.company_id.phone or '')
            },
            'IE': re.sub('[^0-9]', '', self.company_id.inscr_est),
            'IEST': re.sub('[^0-9]', '', self.iest or ''),
            'CRT': self.company_id.fiscal_type,
        }
        if self.company_id.cnae_main_id and self.company_id.inscr_mun:
            emit['IM'] = re.sub('[^0-9]', '', self.company_id.inscr_mun or '')
            emit['CNAE'] = re.sub(
                '[^0-9]', '', self.company_id.cnae_main_id.code or '')
        dest = None
        exporta = None
        if self.commercial_partner_id:
            partner = self.commercial_partner_id
            dest = {
                'tipo': partner.company_type,
                'cnpj_cpf': re.sub('[^0-9]', '', partner.cnpj_cpf or ''),
                'xNome': partner.legal_name or partner.name,
                'enderDest': {
                    'xLgr': str(partner.street or '')[:255],
                    'nro': str(partner.number or '')[:60],
                    'xCpl': str(partner.street2 or '')[:60],
                    'xBairro': str(partner.district or '')[:60],
                    'cMun': '%s%s' % (partner.state_id.ibge_code,
                                      partner.city_id.ibge_code),
                    'xMun': str(partner.city_id.name or '')[:60],
                    'UF': partner.state_id.code,
                    'CEP': re.sub('[^0-9]', '', partner.zip or ''),
                    'cPais': (partner.country_id.bc_code or '')[-4:],
                    'xPais': partner.country_id.name,
                    'fone': re.sub('[^0-9]', '', partner.phone or '')
                },
                'indIEDest': self.ind_ie_dest,
                'IE':  re.sub('[^0-9]', '', partner.inscr_est or ''),
            }
            if self.model == '65':
                dest.update(
                    {'CPF': re.sub('[^0-9]', '', partner.cnpj_cpf or '')})

            if self.ambiente == 'homologacao':
                dest['xNome'] = \
                    'NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL'
                    
            if partner.country_id.id != self.company_id.country_id.id:
                dest['idEstrangeiro'] = re.sub('[^0-9]', '', partner.cnpj_cpf or '000000000000000000')
                dest['enderDest']['UF'] = 'EX'
                dest['enderDest']['xMun'] = 'Exterior'
                dest['enderDest']['cMun'] = '9999999'
                dest['enderDest']['CEP'] = ''
                exporta = {
                    'UFSaidaPais': self.uf_saida_pais_id.code or '',
                    'xLocExporta': self.local_embarque or '',
                    'xLocDespacho': self.local_despacho or '',
                }

        autorizados = []
        if self.company_id.accountant_id:
            autorizados.append({
                'CNPJ': re.sub(
                    '[^0-9]', '', self.company_id.accountant_id.cnpj_cpf)
            })

        eletronic_items = []
        for item in self.eletronic_item_ids:
            eletronic_items.append(
                self._prepare_eletronic_invoice_item(item, self))
        total = {
            # ICMS
            'vBC': "%.02f" % self.valor_bc_icms,
            'vICMS': "%.02f" % self.valor_icms,
            'vICMSDeson': '0.00',
            'vFCP': "%.02f" % self.total_fcp,
            'vBCST': "%.02f" % self.valor_bc_icmsst,
            'vST': "%.02f" % self.valor_icmsst,
            'vFCPST': "%.02f" % self.total_fcp_st,
            'vFCPSTRet': '0.00',
            'vProd': "%.02f" % self.valor_bruto,
            'vFrete': "%.02f" % self.valor_frete,
            'vSeg': "%.02f" % self.valor_seguro,
            'vDesc': "%.02f" % self.valor_desconto,
            'vII': "%.02f" % self.valor_ii,
            'vIPI': "%.02f" % self.valor_ipi,
            'vIPIDevol': '0.00',
            'vPIS': "%.02f" % self.valor_pis,
            'vCOFINS': "%.02f" % self.valor_cofins,
            'vOutro': "%.02f" % self.valor_despesas,
            'vNF': "%.02f" % self.valor_final,
            'vFCPUFDest': "%.02f" % self.valor_icms_fcp_uf_dest,
            'vICMSUFDest': "%.02f" % self.valor_icms_uf_dest,
            'vICMSUFRemet': "%.02f" % self.valor_icms_uf_remet,
            'vTotTrib': "%.02f" % self.valor_estimado_tributos,
        }
        if self.valor_servicos > 0.0:
            issqn_total = {
                'vServ': "%.02f" % self.valor_servicos
                if self.valor_servicos else "",
                'vBC': "%.02f" % self.valor_bc_issqn
                if self.valor_bc_issqn else "",
                'vISS': "%.02f" % self.valor_issqn if self.valor_issqn else "",
                'vPIS': "%.02f" % self.valor_pis_servicos
                if self.valor_pis_servicos else "",
                'vCOFINS': "%.02f" % self.valor_cofins_servicos
                if self.valor_cofins_servicos else "",
                'dCompet': dt_emissao[:10],
                'vDeducao': "",
                'vOutro': "",
                'vISSRet': "%.02f" % self.valor_retencao_issqn
                if self.valor_retencao_issqn else '',
            }
            tributos_retidos = {
                'vRetPIS': "%.02f" % self.valor_retencao_pis
                if self.valor_retencao_pis else '',
                'vRetCOFINS': "%.02f" % self.valor_retencao_cofins
                if self.valor_retencao_cofins else '',
                'vRetCSLL': "%.02f" % self.valor_retencao_csll
                if self.valor_retencao_csll else '',
                'vBCIRRF': "%.02f" % self.valor_bc_irrf
                if self.valor_retencao_irrf else '',
                'vIRRF': "%.02f" % self.valor_retencao_irrf
                if self.valor_retencao_irrf else '',
                'vBCRetPrev': "%.02f" % self.valor_bc_inss
                if self.valor_retencao_inss else '',
                'vRetPrev': "%.02f" % self.valor_retencao_inss
                if self.valor_retencao_inss else '',
            }
        if self.transportadora_id.street:
            end_transp = "%s, %s - %s" % (self.transportadora_id.street,
                                          self.transportadora_id.number or '',
                                          self.transportadora_id.district or '')
            if len(end_transp) > 60:
                end_transp = "%s, %s" % (self.transportadora_id.street,
                                          self.transportadora_id.number or '')
            if len(end_transp) > 60:
                end_transp = end_transp[:60]
        else:
            end_transp = ''
        transp = {
            'modFrete': self.modalidade_frete,
            'transporta': {
                'xNome': self.transportadora_id.legal_name or
                self.transportadora_id.name or '',
                'IE': re.sub('[^0-9]', '',
                             self.transportadora_id.inscr_est or ''),
                'xEnder': end_transp
                if self.transportadora_id else '',
                'xMun': self.transportadora_id.city_id.name or '',
                'UF': self.transportadora_id.state_id.code or ''
            },
            'veicTransp': {
                'placa': self.placa_veiculo or '',
                'UF': self.uf_veiculo or '',
                'RNTC': self.rntc or '',
            }
        }
        cnpj_cpf = re.sub('[^0-9]', '', self.transportadora_id.cnpj_cpf or '')
        if self.transportadora_id.is_company:
            transp['transporta']['CNPJ'] = cnpj_cpf
        else:
            transp['transporta']['CPF'] = cnpj_cpf

        reboques = []
        for item in self.reboque_ids:
            reboques.append({
                'placa': item.placa_veiculo or '',
                'UF': item.uf_veiculo or '',
                'RNTC': item.rntc or '',
                'vagao': item.vagao or '',
                'balsa': item.balsa or '',
            })
        transp['reboque'] = reboques
        volumes = []
        for item in self.volume_ids:
            volumes.append({
                'qVol': item.quantidade_volumes or '',
                'esp': item.especie or '',
                'marca': item.marca or '',
                'nVol': item.numeracao or '',
                'pesoL': "%.03f" % item.peso_liquido
                if item.peso_liquido else '',
                'pesoB': "%.03f" % item.peso_bruto if item.peso_bruto else '',
            })
        transp['vol'] = volumes

        duplicatas = []
        for dup in self.duplicata_ids:
            vencimento = fields.Datetime.from_string(dup.data_vencimento)
            duplicatas.append({
                'nDup': dup.numero_duplicata,
                'dVenc':  vencimento.strftime('%Y-%m-%d'),
                'vDup': "%.02f" % dup.valor
            })
        cobr = {
            'fat': {
                'nFat': self.numero_fatura or '',
                'vOrig': "%.02f" % (
                    self.fatura_liquido + self.fatura_desconto),
                'vDesc': "%.02f" % self.fatura_desconto,
                'vLiq': "%.02f" % self.fatura_liquido,
            },
            'dup': duplicatas
        }
        pag = []
        if self.model == '55':        
            detPag = {
                'indPag': self.payment_term_id.indPag or '0',
                'tPag': self.payment_mode_id.tipo_pagamento or '90',
                'vPag': '0.00',
            }
            pag.append(detPag)
        elif self.model == '65':
            for pagamento in self.pagamento_ids:
                detPag = {
                    'indPag': pagamento.forma_pagamento or '0',
                    'tPag': pagamento.metodo_pagamento or '90',
                    'vPag': "%.02f" % pagamento.valor or '0.00',
                }
                pag.append(detPag)
        
        self.informacoes_complementares = self.informacoes_complementares.\
            replace('\n', '<br />')
        self.informacoes_legais = self.informacoes_legais.replace(
            '\n', '<br />')
        infAdic = {
            'infCpl': self.informacoes_complementares or '',
            'infAdFisco': self.informacoes_legais or '',
        }
        cnpjtec = paramObj.sudo().get_param('NFe.infRespTec.cnpj')
        if cnpjtec:
            cnpjtec = re.sub('[^0-9]', '', cnpjtec)
        infRespTec = {
            'CNPJ': cnpjtec or '',
            'xContato': paramObj.sudo().get_param('NFe.infRespTec.xContato') or '',
            'email': paramObj.sudo().get_param('NFe.infRespTec.email') or '',
            'fone': paramObj.sudo().get_param('NFe.infRespTec.fone') or '',
        }
        compras = {
            'xNEmp': self.nota_empenho or '',
            'xPed': self.pedido_compra or '',
            'xCont': self.contrato_compra or '',
        }

#         responsavel_tecnico = self.company_id.responsavel_tecnico_id
#         infRespTec = {}
# 
#         if responsavel_tecnico:
#             if len(responsavel_tecnico.child_ids) == 0:
#                 raise UserError(
#                     "Adicione um contato para o responsável técnico!")
# 
#             cnpj = re.sub(
#                 '[^0-9]', '', responsavel_tecnico.cnpj_cpf)
#             fone = re.sub(
#                 '[^0-9]', '', responsavel_tecnico.phone)
#             infRespTec = {
#                 'CNPJ': cnpj or '',
#                 'xContato': responsavel_tecnico.child_ids[0].name or '',
#                 'email': responsavel_tecnico.email or '',
#                 'fone': fone or '',
#                 'idCSRT': self.company_id.id_token_csrt or '',
#                 'hashCSRT': self._get_hash_csrt() or '',
#             }
        vals = {
            'Id': 'NFe'+self.chave_nfe if bool(self.chave_nfe) else False,
            'ide': ide,
            'emit': emit,
            'dest': dest,
            'retirada': self._prepare_local_retirada() if self.shipping_mode == '2' else False,
            'entrega': self._prepare_local_entrega() if self.shipping_mode == '1' else False,
            'autXML': autorizados,
            'detalhes': eletronic_items,
            'total': total,
            'pag': pag,
            'transp': transp,
            'infAdic': infAdic,
            'exporta': exporta,
            'compra': compras,
            'infRespTec': infRespTec,
        }

        if self.valor_servicos > 0.0:
            vals.update({
                'ISSQNtot': issqn_total,
                'retTrib': tributos_retidos,
            })
        if len(duplicatas) > 0 and\
                self.fiscal_position_id.finalidade_emissao not in ('2', '4'):
            vals['cobr'] = cobr
#             pag['tPag'] = '01' if pag['tPag'] == '90' else pag['tPag']
#             pag['vPag'] = "%.02f" % self.valor_final

#         if self.model == '65':
#             vals['pag'][0]['tPag'] = self.metodo_pagamento
#             vals['pag'][0]['vPag'] = "%.02f" % self.valor_pago
#             vals['pag'][0]['vTroco'] = "%.02f" % self.troco or '0.00'
# 
#             chave_nfe = self.chave_nfe
#             ambiente = 1 if self.ambiente == 'producao' else 2
#             estado = self.company_id.state_id.ibge_code
# 
#             cid_token = int(self.company_id.id_token_csc)
#             csc = self.company_id.csc
# 
#             c_hash_QR_code = "{0}|2|{1}|{2}{3}".format(
#                 chave_nfe, ambiente, int(cid_token), csc)
#             c_hash_QR_code = hashlib.sha1(c_hash_QR_code.encode()).hexdigest()
# 
#             QR_code_url = "p={0}|2|{1}|{2}|{3}".format(
#                 chave_nfe, ambiente, int(cid_token), c_hash_QR_code)
#             qr_code_server = url_qrcode(estado, str(ambiente))
#             vals['qrCode'] = qr_code_server + QR_code_url
#             vals['urlChave'] = url_qrcode_exibicao(estado, str(ambiente))
        return vals

    @api.multi
    def _prepare_lote(self, lote, nfe_values):
        return {
            'idLote': lote,
            'indSinc': 0, #1 if self.company_id.nfe_sinc else 0,
            'estado': self.company_id.partner_id.state_id.ibge_code,
            'ambiente': 1 if self.ambiente == 'producao' else 2,
            'NFes': [{
                'infNFe': nfe_values
            }],
            'modelo': self.model,
        }

    @api.multi
    def _prepare_local_retirada(self):
        if self.partner_shipping_id:
            res = {
                'tipo': self.partner_shipping_id.company_type,
                'cnpj_cpf': re.sub('[^0-9]', '', self.partner_shipping_id.cnpj_cpf or ''),
                'xNome': self.partner_shipping_id.legal_name or self.partner_shipping_id.name,
                'xLgr': str(self.partner_shipping_id.street or '')[:60],
                'nro': str(self.partner_shipping_id.number or '')[:60],
                'xCpl': str(self.partner_shipping_id.street2 or '')[:60],
                'xBairro': str(self.partner_shipping_id.district or '')[:60],
                'cMun':  '%s%s' % (self.partner_shipping_id.state_id.ibge_code,self.partner_shipping_id.city_id.ibge_code),
                'xMun': str(self.partner_shipping_id.city_id.name or '')[:60],
                'UF': str(self.partner_shipping_id.state_id.code or ''),
                'CEP': re.sub('[^0-9]', '', self.partner_shipping_id.zip or ''),
                'cPais': (self.partner_shipping_id.country_id.bc_code or '')[-4:],
                'xPais': self.partner_shipping_id.country_id.name,
                'fone': re.sub('[^0-9]', '', self.partner_shipping_id.phone or ''),
                'IE': re.sub('[^0-9]', '', self.partner_shipping_id.inscr_est or ''),
            }
        else:
            res = False
        return res

    @api.multi
    def _prepare_local_entrega(self):
        if self.partner_shipping_id:
            res = {
                'tipo': self.partner_shipping_id.company_type,
                'cnpj_cpf': re.sub('[^0-9]', '', self.partner_shipping_id.cnpj_cpf or ''),
                'xNome': self.partner_shipping_id.legal_name or self.partner_shipping_id.name,
                'xLgr': str(self.partner_shipping_id.street or '')[:60],
                'nro': str(self.partner_shipping_id.number or '')[:60],
                'xCpl': str(self.partner_shipping_id.street2 or '')[:60],
                'xBairro': str(self.partner_shipping_id.district or '')[:60],
                'cMun':  '%s%s' % (self.partner_shipping_id.state_id.ibge_code,self.partner_shipping_id.city_id.ibge_code),
                'xMun': str(self.partner_shipping_id.city_id.name or '')[:60],
                'UF': str(self.partner_shipping_id.state_id.code or ''),
                'CEP': re.sub('[^0-9]', '', self.partner_shipping_id.zip or ''),
                'cPais': (self.partner_shipping_id.country_id.bc_code or '')[-4:],
                'xPais': self.partner_shipping_id.country_id.name,
                'fone': re.sub('[^0-9]', '', self.partner_shipping_id.phone or ''),
                'IE': re.sub('[^0-9]', '', self.partner_shipping_id.inscr_est or ''),
            }
        else:
            res = False
        return res

    def _find_attachment_ids_email(self):
        atts = super(InvoiceEletronic, self)._find_attachment_ids_email()
        if self.model not in ('55'):
            return atts

        attachment_obj = self.env['ir.attachment']
        nfe_xml = base64.decodestring(self.nfe_processada)
        logo = base64.decodestring(self.invoice_id.company_id.logo)

        tmpLogo = io.BytesIO()
        tmpLogo.write(logo)
        tmpLogo.seek(0)

        xml_element = etree.fromstring(nfe_xml)
        rascunho = True if not self.data_autorizacao and self.state != 'done' else False
            
        oDanfe = danfe(list_xml=[xml_element], logo=tmpLogo, rascunho=rascunho)

        tmpDanfe = io.BytesIO()
        oDanfe.writeto_pdf(tmpDanfe)

        if danfe:
            danfe_id = attachment_obj.create(dict(
                name="Danfe-%08d.pdf" % self.numero,
                datas_fname="Danfe-%08d.pdf" % self.numero,
                datas=base64.b64encode(tmpDanfe.getvalue()),
                mimetype='application/pdf',
                res_model='account.invoice',
                res_id=self.invoice_id.id,
            ))
            atts.append(danfe_id.id)
        if nfe_xml:
            xml_id = attachment_obj.create(dict(
                name=self.nfe_processada_name,
                datas_fname=self.nfe_processada_name,
                datas=base64.encodestring(nfe_xml),
                mimetype='application/xml',
                res_model='account.invoice',
                res_id=self.invoice_id.id,
            ))
            atts.append(xml_id.id)
        return atts

    @api.multi
    def action_post_validate(self):
        super(InvoiceEletronic, self).action_post_validate()
        if self.model not in ('55', '65'):
            return
        if not bool(self.chave_nfe):
            chave_dict = {
                'cnpj': re.sub('[^0-9]', '', self.company_id.cnpj_cpf),
                'estado': self.company_id.state_id.ibge_code,
                'emissao': self.data_emissao[2:4] + self.data_emissao[5:7],
                'modelo': self.model,
                'numero': self.numero,
                'serie': self.serie.code.zfill(3),
                'tipo': int(self.tipo_emissao),
                'codigo': "%08d" % self.numero_controle
            }
            self.chave_nfe = gerar_chave(ChaveNFe(**chave_dict))

        cert = self.company_id.with_context({'bin_size': False}).nfe_a1_file
        
        if cert:
            cert_pfx = base64.decodestring(cert)
            certificado = Certificado(cert_pfx, self.company_id.nfe_a1_password)

            nfe_values = self._prepare_eletronic_invoice_values()

            lote = self._prepare_lote(self.id, nfe_values)

            xml_enviar = xml_autorizar_nfe(certificado, **lote)

            self.xml_to_send = base64.encodestring(xml_enviar.encode('utf-8'))
            if self.model == '55':
                self.xml_to_send_name = 'nfe-enviar-%s.xml' % self.numero
            else:
                self.xml_to_send_name = 'nfce-enviar-%s.xml' % self.numero            

    @api.multi
    def action_back_to_draft(self):
        if not bool(self.xml_to_send):
            self.action_post_validate()
        self.state = 'draft'

    @api.multi
    def action_regenerate_xml(self):
        self.action_post_validate()

    @api.multi
    def action_send_eletronic_invoice(self):
        super(InvoiceEletronic, self).action_send_eletronic_invoice()

        if self.model not in ('55', '65') or self.state in (
           'done', 'denied', 'cancel'):
            return

        tz = pytz.timezone(self.env.user.tz)
        _logger.info('-> NF-e Sending (%s) (%.2f) - %s' % (self.numero, self.valor_final, self.partner_id.name))
        self.write({
            'state': 'error',
            'data_emissao': datetime.now(tz)
        })

        cert = self.company_id.with_context({'bin_size': False}).nfe_a1_file
        cert_pfx = base64.decodestring(cert)

        certificado = Certificado(cert_pfx, self.company_id.nfe_a1_password)

        if not bool(self.xml_to_send):
            self.action_post_validate()

        if not bool(self.xml_to_send):
            raise UserError(_("XML a enviar é inválido ou inexistente"))
            
        xml_to_send = base64.decodestring(self.xml_to_send).decode('utf-8')

        resposta_recibo = None
        resposta = autorizar_nfe(
            certificado, xml=xml_to_send,
            estado=self.company_id.state_id.ibge_code,
            ambiente=1 if self.ambiente == 'producao' else 2,
            modelo=self.model)#,err108=True)
        retorno = resposta['object'].getchildren()[0] if resposta['object'] else None
        if not retorno:
            self.write({'state': 'error', 'codigo_retorno': 'ERRO',
                        'mensagem_retorno': resposta['received_xml']})
            return
            
        if retorno.cStat == 103:
            _logger.info('-> NF-e Lote recebido com sucesso (%s) (%.2f) - %s' % (self.numero, self.valor_final, self.partner_id.name))
            obj = {
                'estado': self.company_id.partner_id.state_id.ibge_code,
                'ambiente': 1 if self.ambiente == 'producao' else 2,
                'obj': {
                    'ambiente': 1 if self.ambiente == 'producao' else 2,
                    'numero_recibo': retorno.infRec.nRec
                },
                'modelo': self.model,
            }
            self.recibo_nfe = obj['obj']['numero_recibo']
            import time
            tentativas = 0
            while tentativas < 15:
                _logger.info('-> NF-e Verificando Lote (%s) (%.2f) - %s' % (self.numero, self.valor_final, self.partner_id.name))
                time.sleep(3)
                resposta_recibo = retorno_autorizar_nfe(certificado, **obj)
                retorno = resposta_recibo['object'].getchildren()[0]
                if retorno.cStat != 105:
                    break
                tentativas += 1

        if retorno.cStat == 108:
            _logger.info('-> NF-e Serviço Paralisado Momentaneamente (%s) (%.2f) - %s' % (self.numero, self.valor_final, self.partner_id.name))
            self.codigo_retorno = retorno.cStat
            self.mensagem_retorno = retorno.xMotivo
            if self.model == '65': 
                self.write({
                    'state': 'draft',
                    'tipo_emissao': '9',
                    'xml_to_send_name': False,
                    'xml_to_send': False,
                    'qrcode': False,
                })
                self.action_post_validate()

        if retorno.cStat == 105:
            _logger.info('-> eDoc - Lote em processamento (%s) (%.2f) - %s' % (self.numero, self.valor_final, self.partner_id.name))
            self.write({
                'codigo_retorno': retorno.cStat,
                'mensagem_retorno': 'Verifica o processamento mais tarde, %s' % retorno.xMotivo,
            })
            #self.notify_user()
            return False
        elif retorno.cStat != 104:
            _logger.info('-> NF-e Lote processado (%s) (%.2f) - %s' % (self.numero, self.valor_final, self.partner_id.name))
            self.write({
                'codigo_retorno': retorno.cStat,
                'mensagem_retorno': retorno.xMotivo,
            })
            return False
#             self.notify_user()
        else:
            _logger.info('-> NF-e Nota Processada NF-e (%s) (%.2f) - %s' % (self.numero, self.valor_final, self.partner_id.name))
            self.write({
                'codigo_retorno': retorno.protNFe.infProt.cStat,
                'mensagem_retorno': retorno.protNFe.infProt.xMotivo,
            })
            if self.codigo_retorno == '100':
                self.write({
                    'state': 'done',
                    'protocolo_nfe': retorno.protNFe.infProt.nProt,
                    'data_autorizacao': retorno.protNFe.infProt.dhRecbto
                })
#             else:
#                 self.notify_user()
            # Duplicidade de NF-e significa que a nota já está emitida
            # TODO Buscar o protocolo de autorização, por hora só finalizar
            if self.codigo_retorno == '204':
                self.write({
                    'state': 'done', 'codigo_retorno': '100',
                    'mensagem_retorno': 'Autorizado o uso da NF-e'
                })

            # Denegada e nota já está denegada
            if self.codigo_retorno in ('302', '205'):
                self.write({'state': 'denied'})

        self.env['invoice.eletronic.event'].create({
            'code': self.codigo_retorno,
            'name': self.mensagem_retorno,
            'invoice_eletronic_id': self.id,
        })
        self._create_attachment('nfe-envio', self, resposta['sent_xml'])
        self._create_attachment('nfe-ret', self, resposta['received_xml'])
        recibo_xml = resposta['received_xml']
        if resposta_recibo:
            self._create_attachment('rec', self, resposta_recibo['sent_xml'])
            self._create_attachment('rec-ret', self,
                                    resposta_recibo['received_xml'])
            recibo_xml = resposta_recibo['received_xml']

        if self.codigo_retorno == '100':
            nfe_proc = gerar_nfeproc(resposta['sent_xml'], recibo_xml)
            self.write({
                'nfe_processada': base64.encodestring(nfe_proc),
                'nfe_processada_name': "NFe%08d.xml" % self.numero,
            })
        elif self.codigo_retorno == '539':
            motivo = str(retorno.protNFe.infProt.xMotivo)
            p1 = motivo.find('[')
            p2 = motivo.find(']')
            nr_chave = motivo[p1+1:p2]
            p1 = motivo.find('[nRec:')
            p2 = motivo.find(']', p1)
            nr_rec = motivo[p1+6:p2]
            
            nfe_proc = gerar_nfeproc(resposta['sent_xml'], recibo_xml)
            self.write({
                'protocolo_nfe': nr_rec,
                'chave_nfe': nr_chave,
                'state': 'draft',
            })
            
            
#         _logger.info('NF-e (%s) was finished with status %s' % (
#             self.numero, self.codigo_retorno))

    @api.multi
    def generate_nfe_proc(self):
        if self.state in ['cancel', 'done', 'denied']:
            recibo = self.env['ir.attachment'].search([
                ('res_model', '=', 'invoice.eletronic'),
                ('res_id', '=', self.id),
                ('datas_fname', 'like', 'rec-ret')], limit=1)
            if not recibo:
                recibo = self.env['ir.attachment'].search([
                    ('res_model', '=', 'invoice.eletronic'),
                    ('res_id', '=', self.id),
                    ('datas_fname', 'like', 'nfe-ret')], limit=1)
            nfe_envio = self.env['ir.attachment'].search([
                ('res_model', '=', 'invoice.eletronic'),
                ('res_id', '=', self.id),
                ('datas_fname', 'like', 'nfe-envio')], limit=1)
            if nfe_envio.datas and recibo.datas:
                nfe_proc = gerar_nfeproc(
                    base64.decodestring(nfe_envio.datas).decode('utf-8'),
                    base64.decodestring(recibo.datas).decode('utf-8'),
                )
                self.nfe_processada = base64.encodestring(nfe_proc)
                self.nfe_processada_name = "NFe%08d.xml" % self.numero
        else:
            raise UserError(_('A NFe não está validada'))

    @api.multi
    def action_cancel_document(self, context=None, justificativa=None):
        if self.model not in ('55', '65'):
            return super(InvoiceEletronic, self).action_cancel_document(
                justificativa=justificativa)

        if not justificativa:
            return {
                'name': _('Cancelamento NFe'),
                'type': 'ir.actions.act_window',
                'res_model': 'wizard.cancel.nfe',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_edoc_id': self.id
                }
            }

        _logger.info('Cancelling NF-e (%s)' % self.numero)
        cert = self.company_id.with_context({'bin_size': False}).nfe_a1_file
        cert_pfx = base64.decodestring(cert)
        certificado = Certificado(cert_pfx, self.company_id.nfe_a1_password)

        id_canc = "ID110111%s%02d" % (
            self.chave_nfe, self.sequencial_evento)

#         tz = timezone(self.env.user.tz)
#         dt_evento = datetime.now(tz).replace(microsecond=0).isoformat()
        diferenca = timedelta(hours=-3)
        if (time.timezone / 3600.0) == 0.0:
            dt_evento = datetime.now(timezone(diferenca)).replace(microsecond=0).isoformat()
        else:
            dt_evento = datetime.now().replace(microsecond=0).replace(tzinfo=timezone(diferenca)).isoformat()

        cancelamento = {
            'idLote': self.id,
            'estado': self.company_id.state_id.ibge_code,
            'ambiente': 2 if self.ambiente == 'homologacao' else 1,
            'eventos': [{
                'Id': id_canc,
                'cOrgao': self.company_id.state_id.ibge_code,
                'tpAmb': 2 if self.ambiente == 'homologacao' else 1,
                'CNPJ': re.sub('[^0-9]', '', self.company_id.cnpj_cpf),
                'chNFe': self.chave_nfe,
                'dhEvento': dt_evento,
                'nSeqEvento': self.sequencial_evento,
                'nProt': self.protocolo_nfe,
                'xJust': justificativa,
                'tpEvento': '110111',
                'descEvento': 'Cancelamento',
            }],
            'modelo': self.model,
        }

        resp = recepcao_evento_cancelamento(certificado, **cancelamento)
        resposta = resp['object'].getchildren()[0]
        if resposta.cStat == 128 and \
                resposta.retEvento.infEvento.cStat in (135, 136, 155):
            self.write({
                'state': 'cancel',
                'codigo_retorno': resposta.retEvento.infEvento.cStat,
                'mensagem_retorno': resposta.retEvento.infEvento.xMotivo,
                'sequencial_evento': self.sequencial_evento + 1,
            })
        else:
            code, motive = None, None
            if resposta.cStat == 128:
                code = resposta.retEvento.infEvento.cStat
                motive = resposta.retEvento.infEvento.xMotivo
            else:
                code = resposta.cStat
                motive = resposta.xMotivo
            if code == 573:  # Duplicidade, já cancelado
                return self.action_get_status()

            return self._create_response_cancel(
                code, motive, resp, justificativa)

        self.env['invoice.eletronic.event'].create({
            'code': self.codigo_retorno,
            'name': self.mensagem_retorno,
            'invoice_eletronic_id': self.id,
        })
        self._create_attachment('canc', self, resp['sent_xml'])
        self._create_attachment('canc-ret', self, resp['received_xml'])
        if self.nfe_processada:
            nfe_processada = base64.decodestring(self.nfe_processada)
        elif self.xml_to_send:
            nfe_processada = base64.decodestring(self.xml_to_send)
        else:
            nfe_processada = ''
        nfe_proc_cancel = gerar_nfeproc_cancel(nfe_processada, resp['received_xml'].encode())
        if nfe_proc_cancel:
            self.nfe_processada = base64.encodestring(nfe_proc_cancel)
        _logger.info('Cancelling NF-e (%s) was finished with status %s' % (self.numero, self.codigo_retorno))

    def action_get_status(self):
        cert = self.company_id.with_context({'bin_size': False}).nfe_a1_file
        cert_pfx = base64.decodestring(cert)
        certificado = Certificado(cert_pfx, self.company_id.nfe_a1_password)
        consulta = {
            'estado': self.company_id.state_id.ibge_code,
            'ambiente': 2 if self.ambiente == 'homologacao' else 1,
            'modelo': self.model,
            'obj': {
                'chave_nfe': self.chave_nfe,
                'ambiente': 2 if self.ambiente == 'homologacao' else 1,
            }
        }
        resp = consultar_protocolo_nfe(certificado, **consulta)
        self._create_attachment('consul', self, resp['sent_xml'])
        self._create_attachment('resp_consul', self, resp['received_xml'])
        retorno_consulta = resp['object'].getchildren()[0]
        if retorno_consulta.cStat == 100:
            self.state = 'done'
            self.codigo_retorno = retorno_consulta.cStat
            self.mensagem_retorno = retorno_consulta.xMotivo
        elif retorno_consulta.cStat == 101:
            self.state = 'cancel'
            self.codigo_retorno = retorno_consulta.cStat
            self.mensagem_retorno = retorno_consulta.xMotivo
            resp['received_xml'] = etree.tostring(retorno_consulta, encoding=str)

            self.env['invoice.eletronic.event'].create({
                'code': self.codigo_retorno,
                'name': self.mensagem_retorno,
                'invoice_eletronic_id': self.id,
            })
            self._create_attachment('canc', self, resp['sent_xml'])
            self._create_attachment('canc-ret', self, resp['received_xml'])
            nfe_processada = base64.decodestring(self.nfe_processada)

            nfe_proc_cancel = gerar_nfeproc_cancel(
                nfe_processada, resp['received_xml'].encode())
            if nfe_proc_cancel:
                self.nfe_processada = base64.encodestring(nfe_proc_cancel)
        elif retorno_consulta.cStat == 539:
            self.state = 'error'
            self.codigo_retorno = retorno_consulta.cStat
            self.mensagem_retorno = retorno_consulta.xMotivo + '\n*** Chave foi corrigida'
            self.chave_nfe = str(retorno_consulta.chNFe)
        else:
            message = "%s - %s" % (retorno_consulta.cStat,
                                   retorno_consulta.xMotivo)
            raise UserError(message)

    def _create_response_cancel(self, code, motive, response, justificativa):
        message = "%s - %s" % (code, motive)
        wiz = self.env['wizard.cancel.nfe'].create({
            'edoc_id': self.id,
            'justificativa': justificativa,
            'state': 'error',
            'message': message,
            'sent_xml': base64.b64encode(
                response['sent_xml'].encode('utf-8')),
            'sent_xml_name': 'cancelamento-envio.xml',
            'received_xml': base64.b64encode(
                response['received_xml'].encode('utf-8')),
            'received_xml_name': 'cancelamento-retorno.xml',
        })
        return {
            'name': _('Cancelamento NFe'),
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.cancel.nfe',
            'res_id': wiz.id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def _get_hash_csrt(self):
        chave_nfe = self.chave_nfe
        csrt = self.company_id.csrt

        if not csrt:
            return

        hash_csrt = "{0}{1}".format(csrt, chave_nfe)
        hash_csrt = base64.b64encode(
            hashlib.sha1(hash_csrt.encode()).digest())

        return hash_csrt.decode("utf-8")

    @api.multi
    def query_status_webservice(self, context=None, response_type='notify'):
        """
        :param context: default
        :param response_type: tipo de resposta, caso seja notify
        será gerado um stick notificando o usuário
        :return: notificação ou objeto com dados da consulta
        """
        cert = self.company_id.with_context({'bin_size': False}).nfe_a1_file
        cert_pfx = base64.decodestring(cert)
        certificado = Certificado(cert_pfx, self.company_id.nfe_a1_password)
        query = dict(
            estado=self.env.user.company_id.partner_id.state_id.ibge_code,
            obj=dict(
                ambiente=int(self.env.user.company_id.tipo_ambiente),
                estado=int(self.env.user.company_id.state_id.ibge_code),
            ),
        )

        if self.model:
            query['modelo'] = self.model
        if self.ambiente:
            query['ambiente'] = 1 if self.ambiente == 'producao' else 2
        else:
            query['ambiente'] = int(self.env.user.company_id.tipo_ambiente)

        status = nfe_status_servico(certificado, **query)
        return_query = status['object'].getchildren()[0]
        if response_type == 'notify':
            user = self.env.user
            message = u'Cód Status: %s <br/>' \
                      u'Descrição: %s' % (
                return_query.cStat, return_query.xMotivo)
            title = _('Resposta da Consulta')

            return user.notify_info(message=message, title=title, sticky=False)

        return return_query
