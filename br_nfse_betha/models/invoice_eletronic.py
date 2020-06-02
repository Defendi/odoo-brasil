import re
import pytz
import time
import base64
import logging
from urllib.request import urlopen
from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTFT

_logger = logging.getLogger(__name__)

try:
    from pytrustnfe.nfse.betha import xml_recepcionar_lote_rps
    from pytrustnfe.nfse.betha import consultar_lote_rps
    from pytrustnfe.nfse.betha import recepcionar_lote_rps
    from pytrustnfe.nfse.betha import cancelar_nfse
    from pytrustnfe.certificado import Certificado
except ImportError:
    _logger.debug('Cannot import pytrustnfe')


STATE = {'edit': [('readonly', False)]}

class InvoiceEletronicItem(models.Model):
    _inherit = 'invoice.eletronic.item'

    danfe = fields.Binary(string="Danfe Betha", readonly=True)
    danfe_name = fields.Char(string="Danfe Betha", size=100, readonly=True)

    codigo_tributacao_municipio = fields.Char(
        string="Cód. Tribut. Munic.", size=20, readonly=True,
        help="Código de Tributação no Munípio", states=STATE)

class InvoiceEletronic(models.Model):
    _inherit = 'invoice.eletronic'

    model = fields.Selection(selection_add=[('004', 'NFS-e - Provedor BETHA')])

    enforce_iss_betha = fields.Selection(
        [('1', "1 - Exigível"),
         ('2', "2 - Não incidência"),
         ('3', "3 - Isenção"),
         ('4', "4 - Exportação"),
         ('5', "5 - Imunidade"),
         ('6', "6 - Suspensa por Decisão Judicial"),
         ('7', "7 - Suspensa por Processo Admin."),
        ], "ISS Exigibilidade", default='1', readonly=True, states=STATE)

    @api.multi
    def _hook_validation(self):
        errors = super(InvoiceEletronic, self)._hook_validation()
        if self.model == '004':
            issqn_codigo = ''
#             if not self.company_id.inscr_mun:
#                 errors.append('Inscrição municipal obrigatória')
            if not self.company_id.cnae_main_id.code:
                errors.append('CNAE Principal da empresa obrigatório')
            for eletr in self.eletronic_item_ids:
                prod = "Produto: %s - %s" % (eletr.product_id.default_code,
                                              eletr.product_id.name)
                if eletr.tipo_produto == 'product':
                    errors.append(
                        'Esse documento permite apenas serviços - %s' % prod)
                if eletr.tipo_produto == 'service':
                    if not eletr.issqn_codigo:
                        errors.append('%s - Código de Serviço' % prod)
                    if not issqn_codigo:
                        issqn_codigo = eletr.issqn_codigo
                    if issqn_codigo != eletr.issqn_codigo:
                        errors.append('%s - Apenas itens com o mesmo código \
                                      de serviço podem ser enviados' % prod)

        return errors

    @api.multi
    def _prepare_eletronic_invoice_values(self):
        res = super(InvoiceEletronic, self)._prepare_eletronic_invoice_values()
        if self.model == '004':
            tz = pytz.timezone(self.env.user.partner_id.tz) or pytz.utc
            dt_emissao = datetime.strptime(self.data_emissao, DTFT)
            dt_emissao = pytz.utc.localize(dt_emissao).astimezone(tz)
            dt_emissao = dt_emissao.strftime('%Y-%m-%d')
            dt_competencia = dt_emissao

            partner = self.commercial_partner_id
            city_tomador = partner.city_id
            tomador = {
                'tipo_cpfcnpj': 2 if partner.is_company else 1,
                'cnpj_cpf': re.sub('[^0-9]', '', partner.cnpj_cpf or ''),
                'razao_social': partner.legal_name or partner.name,
                'logradouro': partner.street or '',
                'numero': partner.number or '',
                'complemento': partner.street2 or '',
                'bairro': partner.district or 'Sem Bairro',
                'cidade': '%s%s' % (city_tomador.state_id.ibge_code, city_tomador.ibge_code),
                'uf': partner.state_id.code,
                'cep': re.sub('[^0-9]', '', partner.zip),
                'telefone': re.sub('[^0-9]', '', partner.phone or ''),
                'inscricao_municipal': re.sub('[^0-9]', '', partner.inscr_mun or ''),
                'email': self.partner_id.email or partner.email or '',
            }
            city_prestador = self.company_id.partner_id.city_id
            pais_prestador = self.company_id.partner_id.country_id
            prestador = {
                'cnpj': re.sub('[^0-9]', '', self.company_id.partner_id.cnpj_cpf or ''),
                'inscricao_municipal': re.sub('[^0-9]', '', self.company_id.partner_id.inscr_mun or ''),
                'cidade': '%s%s' % (city_prestador.state_id.ibge_code,city_prestador.ibge_code),
                'cnae': re.sub('[^0-9]', '', self.company_id.cnae_main_id.code)
            }

            itens_servico = []
            descricao = ''
            codigo_servico = ''
            for item in self.eletronic_item_ids:
                descricao += item.name + '\n'
                itens_servico.append({
                    'descricao': item.name,
                    'quantidade': str("%.2f" % item.quantidade),
                    'valor_unitario': str("%.2f" % item.preco_unitario),
                    'valor_iss_retido': 1 if item.issqn_valor_retencao > 0.0 else 2,
                })
                codigo_servico = re.sub('[^0-9]', '', item.issqn_codigo)
                codigo_tributacao_municipio = self.eletronic_item_ids[0].codigo_tributacao_municipio
                codigo_municipio_recolhimento = '%s%s' % (item.state_id.ibge_code,item.city_id.ibge_code)

            rps = {
                'numero': self.numero,
                'serie': self.serie.code or '',
                'tipo_rps': '1',
                'data_emissao': dt_emissao,
                'data_competencia': dt_competencia,
                'natureza_operacao': '1',  # Tributada no municipio
                'regime_tributacao': '2',  # Estimativa
                'optante_simples': '2' if self.company_id.fiscal_type == '3' else '1', # 1 - Sim, 2 - Não
                'incentivador_cultural': '2',  # 2 - Não
                'status': '1',  # 1 - Normal
                'valor_servico': str("%.2f" % self.valor_bruto),
                'valor_deducao': '0.00',
                'valor_pis': str("%.2f" % self.valor_retencao_pis),
                'valor_cofins': str("%.2f" % self.valor_retencao_cofins),
                'valor_inss': str("%.2f" % self.valor_retencao_inss),
                'valor_ir': str("%.2f" % self.valor_retencao_irrf),
                'valor_csll': str("%.2f" % self.valor_retencao_csll),
                'outras_retencoes': str("%.2f" % self.valor_retencao_outras),
                'iss_retido': '1' if self.valor_retencao_issqn > 0 else '2',
                'desconto_incondicionado': str("%.2f" % self.valor_desconto),
                'desconto_condicionado': '0.00',    
                'base_calculo': str("%.2f" % self.valor_final),
                'aliquota_issqn': str("%.4f" % (self.eletronic_item_ids[0].issqn_aliquota / 100)),
                'valor_liquido_nfse': str("%.2f" % self.valor_final),
                'codigo_servico': int(codigo_servico),
                'exigibilidade_iss': self.enforce_iss_betha,
                'codigo_tributacao_municipio': codigo_tributacao_municipio if codigo_tributacao_municipio else '',
                # '01.07.00 / 00010700',
                'descricao': descricao,
                'codigo_municipio': codigo_municipio_recolhimento,
                'itens_servico': itens_servico,
                'tomador': tomador,
                'prestador': prestador,
            }

            aliq_ret_iss = 0.0
            if rps['iss_retido'] == '1':
                rps['resp_retencao'] = '1'
                aliq_ret_iss = (self.valor_retencao_issqn / (self.valor_bruto - self.valor_desconto)) * 100
            
            if codigo_municipio_recolhimento != prestador['cidade']:
                rps['valor_iss_retido'] = str("%.2f" % self.valor_retencao_issqn)
                rps['aliquota_iss_retido'] = str("%.2f" % aliq_ret_iss)
            
            if self.enforce_iss_betha == '4':
                rps['codigo_pais'] = tomador['pais']
            
            nfse_vals = {
                'numero_lote': self.id,
                'inscricao_municipal': prestador['inscricao_municipal'],
                'cnpj_prestador': prestador['cnpj'],
                'lista_rps': [rps],
            }

            res.update(nfse_vals)
        return res

    @api.multi
    def action_post_validate(self):
        super(InvoiceEletronic, self).action_post_validate()
        if self.model not in ('004'):
            return

        cert = self.company_id.with_context({'bin_size': False}).nfe_a1_file
        cert_pfx = base64.decodestring(cert)

        certificado = Certificado(cert_pfx, self.company_id.nfe_a1_password)

        nfse_values = self._prepare_eletronic_invoice_values()
        xml_enviar = xml_recepcionar_lote_rps(certificado, nfse=nfse_values)
        #xml_enviar = etree.tostring(xml_enviar)

        self.xml_to_send = base64.encodestring(bytes(xml_enviar, 'utf-8'))
        self.xml_to_send_name = 'nfse-betha-enviar-%s.xml' % self.numero

    def _find_attachment_ids_email(self):
        atts = super(InvoiceEletronic, self)._find_attachment_ids_email()
        if self.model not in ('004'):
            return atts

        attachment_obj = self.env['ir.attachment']
        danfe_report = self.env['ir.actions.report'].search(
            [('report_name', '=',
              'br_nfse_ginfes.main_template_br_nfse_danfe_ginfes')])
        report_service = danfe_report.xml_id
        report_name = safe_eval(danfe_report.print_report_name,
                                {'object': self, 'time': time})
        danfse, dummy = self.env.ref(report_service).render_qweb_pdf([self.id])
        filename = "%s.%s" % (report_name, "pdf")
        if danfse:
            danfe_id = attachment_obj.create(dict(
                name=filename,
                datas_fname=filename,
                datas=base64.b64encode(danfse),
                mimetype='application/pdf',
                res_model='account.invoice',
                res_id=self.invoice_id.id,
            ))
            atts.append(danfe_id.id)
        return atts

    @api.multi
    def action_send_eletronic_invoice(self):
        super(InvoiceEletronic, self).action_send_eletronic_invoice()
        if self.model == '004' and self.state not in ('done', 'cancel'):
            self.state = 'error'

            cert = self.company_id.with_context({'bin_size': False}).nfe_a1_file
            cert_pfx = base64.decodestring(cert)

            certificado = Certificado(cert_pfx, self.company_id.nfe_a1_password)

            consulta_lote = None
            recebe_lote = None

            # Envia o lote apenas se não existir protocolo
            if not self.verify_code: 
                xml_to_send = base64.decodestring(self.xml_to_send)

                recebe_lote = recepcionar_lote_rps(certificado, xml=xml_to_send, ambiente=self.ambiente)

                retorno = recebe_lote['object']
                if retorno is not None:
                    if "NumeroLote" in dir(retorno):
                        self.state = 'waiting'
                        self.verify_code = retorno.Protocolo
                        self.nfe_processada = base64.encodestring(recebe_lote['sent_xml'])
                        self.nfe_processada_name = 'nfse-betha-envida-%s.xml' % self.numero
                        time.sleep(5)  # Espera alguns segundos antes de consultar
                    else:
                        self.codigo_retorno = retorno.ListaMensagemRetorno.MensagemRetorno.Codigo
                        self.mensagem_retorno = retorno.ListaMensagemRetorno.MensagemRetorno.Mensagem
                        self._create_attachment('nfse-ret', self, recebe_lote['received_xml'])
                        return
                else:
                    self.codigo_retorno = '000'
                    self.mensagem_retorno = recebe_lote['received_xml']
                    return
                    
            obj = {
                'cnpj_prestador': re.sub(
                    '[^0-9]', '', self.company_id.cnpj_cpf),
                'protocolo': self.verify_code,
            }
            consulta_lote = consultar_lote_rps(certificado, consulta=obj, ambiente=self.ambiente)
            retLote = consulta_lote['object']
  
            if "Situacao" in dir(retLote):
                if retLote.Situacao in (1,2,3):  # Retorno com erro
                    self.codigo_retorno = retLote.ListaMensagemRetorno.MensagemRetorno.Codigo
                    self.mensagem_retorno = retLote.ListaMensagemRetorno.MensagemRetorno.Mensagem
                    self.state = 'error'
                elif retLote.Situacao == 4:
                    if "ListaNfse" in dir(retLote):
                        self.state = 'done'
                        self.codigo_retorno = '100'
                        self.mensagem_retorno = 'NFSe emitida com sucesso'
                        self.verify_code = retLote.ListaNfse.CompNfse.Nfse.InfNfse.CodigoVerificacao
                        self.numero_nfse = retLote.ListaNfse.CompNfse.Nfse.InfNfse.Numero
                        self.url_danfe = retLote.ListaNfse.CompNfse.Nfse.InfNfse.OutrasInformacoes
                        if self.url_danfe:
                            response = urlopen(self.url_danfe)
                            self.danfe = base64.encodestring(response.read())
                            self.danfe_name = 'danfe-betha-%s.pdf' % self.numero_nfse
                    else:
                        self.codigo_retorno = retLote.ListaMensagemRetorno.MensagemRetorno.Codigo
                        self.mensagem_retorno = retLote.ListaMensagemRetorno.MensagemRetorno.Mensagem
  
                else:
                    self.state = 'waiting'
                    self.codigo_retorno = '4'
                    self.mensagem_retorno = 'Lote aguardando processamento.'
            else:
                self.codigo_retorno = retLote.ListaMensagemRetorno.MensagemRetorno.Codigo
                self.mensagem_retorno = retLote.ListaMensagemRetorno.MensagemRetorno.Mensagem
  
            self.env['invoice.eletronic.event'].create({
                'code': self.codigo_retorno,
                'name': self.mensagem_retorno,
                'invoice_eletronic_id': self.id,
            })
            if recebe_lote:
                self._create_attachment('nfse-ret', self, recebe_lote['received_xml'])
            if consulta_lote:
                self._create_attachment('rec', self, consulta_lote['sent_xml'])
                self._create_attachment('rec-ret', self, consulta_lote['received_xml'])

    @api.multi
    def action_cancel_document(self, context=None, justificativa=None):
        if self.model not in ('004'):
            return super(InvoiceEletronic, self).action_cancel_document(
                justificativa=justificativa)

        cert = self.company_id.with_context({'bin_size': False}).nfe_a1_file
        cert_pfx = base64.decodestring(cert)

        certificado = Certificado(cert_pfx, self.company_id.nfe_a1_password)

        company = self.company_id
        city_prestador = self.company_id.partner_id.city_id
        canc = {
            'cnpj_prestador': re.sub('[^0-9]', '', company.cnpj_cpf),
            'inscricao_municipal': re.sub('[^0-9]', '', company.inscr_mun) if company.inscr_mun else '',
            'cidade': '%s%s' % (city_prestador.state_id.ibge_code, city_prestador.ibge_code),
            'numero_nfse': self.numero_nfse,
            'codigo_cancelamento': '1',
        }
        cancel = cancelar_nfse(certificado, cancelamento=canc, ambiente=self.ambiente)
        
        if hasattr(cancel['object'], 'RetCancelamento'):
            self.state = 'cancel'
            self.codigo_retorno = '100'
            self.url_danfe = False
            self.danfe = False
            self.mensagem_retorno = 'Nota Fiscal de Serviço Cancelada'
        else:
            retorno = cancel['object'].ListaMensagemRetorno.MensagemRetorno
            # E79 - Nota já está cancelada
            if retorno.Codigo == 'E79':
                self.state = 'cancel'
                self.url_danfe = False
                self.danfe = False
                self.codigo_retorno = '100'
                self.mensagem_retorno = 'Nota Fiscal de Serviço Cancelada'

            self.env['invoice.eletronic.event'].create({
                'code': retorno.Codigo,
                'name': retorno.Mensagem,
                'invoice_eletronic_id': self.id,
            })
        self._create_attachment('canc', self, cancel['sent_xml'])
        self._create_attachment('canc-ret', self, cancel['received_xml'])
