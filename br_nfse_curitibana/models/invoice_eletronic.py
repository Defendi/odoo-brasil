import re
import base64
import pytz
import time
import logging
from datetime import datetime
from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTFT

_logger = logging.getLogger(__name__)

try:
    from pytrustnfe.nfse.curitibana import xml_gerar_rps
    from pytrustnfe.nfse.curitibana import xml_gerar_lote
    from pytrustnfe.nfse.curitibana import send_lote
    from pytrustnfe.nfse.curitibana import valid_xml
    from pytrustnfe.certificado import Certificado
except ImportError:
    _logger.error('Cannot import pytrustnfe', exc_info=True)

STATE = {'edit': [('readonly', False)]}

class InvoiceEletronic(models.Model):
    _inherit = 'invoice.eletronic'

    model = fields.Selection(selection_add=[('041', 'Nota Curitibana')])

    @api.multi
    def _hook_validation(self):
        errors = super(InvoiceEletronic, self)._hook_validation()
        if self.model == '041':
            pass
#             if not self.company_id.inscr_mun:
#                 errors.append('Inscrição municipal obrigatória')
#             if not self.company_id.cnae_main_id.code:
#                 errors.append('CNAE Principal da empresa obrigatório')
#             for eletr in self.eletronic_item_ids:
#                 prod = "Produto: %s - %s" % (eletr.product_id.default_code,
#                                               eletr.product_id.name)
#                 if not eletr.codigo_tributacao_municipio:
#                     errors.append(
#                         'Código de Tributação no Munípio obrigatório - %s' %
#                         prod)
        return errors

    @api.multi
    def _prepare_eletronic_invoice_values(self):
        res = super(InvoiceEletronic, self)._prepare_eletronic_invoice_values()
        if self.model != '041':
            return res

        tz = pytz.timezone(self.env.user.partner_id.tz) or pytz.utc
        dt_emissao = datetime.strptime(self.data_emissao, DTFT)
        dt_emissao = pytz.utc.localize(dt_emissao).astimezone(tz)
        dt_emissao = dt_emissao.strftime('%Y-%m-%dT%H:%M:%S')
        #dt_emissao = dt_emissao.strftime('%Y-%m-%d')
        dt_competencia = dt_emissao

        partner = self.commercial_partner_id
        city_tomador = partner.city_id
        tomador = {
            'tipo_cpfcnpj': 2 if partner.is_company else 1,
            'cnpj_cpf': re.sub('[^0-9]', '',partner.cnpj_cpf or ''),
            'razao_social': partner.legal_name or partner.name,
            'logradouro': partner.street or '',
            'numero': partner.number or '',
            'complemento': partner.street2 or '',
            'bairro': partner.district or 'Sem Bairro',
            'cidade': '%s%s' % (city_tomador.state_id.ibge_code,city_tomador.ibge_code),
            'pais': '%s' % (partner.country_id.ibge_code),
            'uf': partner.state_id.code,
            'cep': re.sub('[^0-9]', '', partner.zip),
            'telefone': re.sub('[^0-9]', '', partner.phone[:11] or ''),
            'inscricao_municipal': re.sub('[^0-9]', '', partner.inscr_mun or ''),
            'email': self.partner_id.email or partner.email or '',
        }
        city_prestador = self.company_id.partner_id.city_id
        pais_prestador = self.company_id.partner_id.country_id
        prestador = {
            'cnpj': re.sub('[^0-9]', '', self.company_id.partner_id.cnpj_cpf or ''),
            'inscricao_municipal': re.sub('[^0-9]', '', self.company_id.partner_id.inscr_mun or ''),
            'cidade': '%s%s' % (city_prestador.state_id.ibge_code,city_prestador.ibge_code),
            'pais': '%s' % (pais_prestador.ibge_code),
            'cnae': re.sub('[^0-9]', '', self.company_id.cnae_main_id.code)
        }
        
        itens_servico = []
        descricao = ''
        codigo_servico = ''
        iss_base = 0.0
        iss_retido = 0.0
        iss_valor = 0.0
        for item in self.eletronic_item_ids:
            descricao += item.name + ' '
            itens_servico.append({
                'descricao': item.name,
                'quantidade': str("%.2f" % item.quantidade),
                'valor_unitario': str("%.2f" % item.preco_unitario),
                'valor_iss_retido': 1 if item.issqn_valor_retencao > 0.0 else 2,
            })
            iss_base += item.issqn_base_calculo
            iss_valor += item.issqn_valor_retencao
            iss_valor += item.issqn_valor 
            codigo_servico = re.sub('[^0-9]', '', item.issqn_codigo)
            codigo_tributacao_municipio = item.product_id.service_type_id.codigo_tributacao_municipio
            if item.city_id.ibge_code:
                codigo_municipio_recolhimento = '%s%s' % (item.state_id.ibge_code,item.city_id.ibge_code)
            else:
                codigo_municipio_recolhimento = prestador['cidade']

        rps = {
            'numero': self.numero,
            'serie': self.serie.code or '',
            'tipo_rps': '1',
            'data_emissao': dt_emissao,
            #'data_competencia': dt_competencia,
            'natureza_operacao': '1' if codigo_municipio_recolhimento == prestador['cidade'] else '2',
            #'regime_tributacao': '2',  # Estimativa
            'optante_simples': '2' if self.company_id.fiscal_type == '3' else '1', # 1 - Sim, 2 - Não
            'incentivador_cultural': '2',  # 2 - Não
            'status': '1',  # 1 - Normal
            'valor_servico': str("%.2f" % self.valor_servicos),
            'valor_deducao': '0.00',
            'valor_pis': str("%.2f" % self.valor_retencao_pis),
            'valor_cofins': str("%.2f" % self.valor_retencao_cofins),
            'valor_inss': str("%.2f" % self.valor_retencao_inss),
            'valor_ir': str("%.2f" % self.valor_retencao_irrf),
            'valor_csll': str("%.2f" % self.valor_retencao_csll),
            'outras_retencoes': str("%.2f" % self.valor_retencao_outras),
            'iss_retido': '1' if self.valor_retencao_issqn > 0 else '2',
            'valor_iss': str("%.2f" % iss_valor),
            'valor_iss_retido': str("%.2f" % self.valor_retencao_issqn),
            'desconto_incondicionado': str("%.2f" % self.valor_desconto),
            'desconto_condicionado': '0.00',    
            'base_calculo': str("%.2f" % self.valor_bc_issqn),
            'aliquota_iss': str("%.4f" % (self.eletronic_item_ids[0].issqn_aliquota / 100)),
            'valor_liquido': str("%.2f" % self.valor_final),
            'codigo_servico': codigo_servico,
            #TODO: Verificar codigo de tributação do municipio
            'codigo_tributacao_municipio': codigo_tributacao_municipio if codigo_tributacao_municipio else '',
            # '01.07.00 / 00010700',
            'descricao': descricao,
            'codigo_municipio': codigo_municipio_recolhimento,
            #'codigo_pais': prestador['pais'],
            'itens_servico': itens_servico,
            'tomador': tomador,
            'prestador': prestador,
        }
        
        if rps['iss_retido'] == '1':
            rps.pop('valor_iss')
        else:
            rps.pop('valor_iss_retido')
        
#         nfse_vals = {
#             'numero_lote': self.id,
#             'inscricao_municipal': prestador['inscricao_municipal'],
#             'cnpj_prestador': prestador['cnpj'],
#             'lista_rps': [rps],
#         }

        res.update(rps)
        return res

    def _find_attachment_ids_email(self):
        atts = super(InvoiceEletronic, self)._find_attachment_ids_email()
        if self.model not in ('041'):
            return atts
#         attachment_obj = self.env['ir.attachment']
#         attachment_ids = attachment_obj.search(
#             [('res_model', '=', 'invoice.eletronic'),
#              ('res_id', '=', self.id),
#              ('name', 'like', 'nfse-ret')], limit=1, order='id desc')
# 
#         for attachment in attachment_ids:
#             xml_id = attachment_obj.create(dict(
#                 name=attachment.name,
#                 datas_fname=attachment.datas_fname,
#                 datas=attachment.datas,
#                 mimetype=attachment.mimetype,
#                 res_model='account.invoice',
#                 res_id=self.invoice_id.id,
#             ))
#             atts.append(xml_id.id)

#         danfe_report = self.env['ir.actions.report'].search(
#             [('report_name', '=',
#               'br_nfse_carioca.main_template_br_nfse_carioca')])
#         report_service = danfe_report.xml_id
#         danfse, dummy = self.env.ref(report_service).render_qweb_pdf([self.id])
#         report_name = safe_eval(danfe_report.print_report_name,
#                                 {'object': self, 'time': time})
#         filename = "%s.%s" % (report_name, "pdf")
#         if danfse:
#             danfe_id = attachment_obj.create(dict(
#                 name=filename,
#                 datas_fname=filename,
#                 datas=base64.b64encode(danfse),
#                 mimetype='application/pdf',
#                 res_model='account.invoice',
#                 res_id=self.invoice_id.id,
#             ))
#             atts.append(danfe_id.id)

        return atts

    @api.multi
    def action_post_validate(self):
        super(InvoiceEletronic, self).action_post_validate()
        if self.model not in ('041'):
            return

        cert = self.company_id.with_context({'bin_size': False}).nfe_a1_file
        cert_pfx = base64.decodestring(cert)

        certificado = Certificado(cert_pfx, self.company_id.nfe_a1_password)

        nfse_values = self._prepare_eletronic_invoice_values()
        xml_enviar = xml_gerar_rps(certificado, rps=nfse_values)

        self.xml_to_send = base64.encodestring(xml_enviar.encode())
        self.xml_to_send_name = 'nfse-enviar-%s.xml' % self.numero

    @api.multi
    def action_send_eletronic_invoice(self):
        super(InvoiceEletronic, self).action_send_eletronic_invoice()
        if self.model != '041' or self.state in ('done', 'cancel'):
            return

        rps = base64.decodestring(self.xml_to_send)

        lote = {
            'numero_lote': str(self.id),
            'inscricao_municipal': re.sub('[^0-9]', '',self.env.user.company_id.inscr_mun or ''),
            'cnpj_prestador': re.sub('[^0-9]', '',self.env.user.company_id.cnpj_cpf or ''),
            'lista_rps': [rps],
        }

        cert = self.company_id.with_context({'bin_size': False}).nfe_a1_file
        cert_pfx = base64.decodestring(cert)

        certificado = Certificado(cert_pfx, self.company_id.nfe_a1_password)

        xml_to_send = xml_gerar_lote(certificado, lote=lote)

        if bool(xml_to_send):
            self._create_attachment('nfse-lote-envio', self, xml_to_send)
        self.state = 'error'
        self.env.cr.commit()
        
        enviar_nfse = valid_xml(certificado, xml=xml_to_send, ambiente='producao')#self.ambiente)

        retorno = enviar_nfse['object']
        if bool(retorno):
            self._create_attachment(
                'nfse-envio', self, enviar_nfse['sent_xml'])
            self._create_attachment(
                'nfse-ret', self, enviar_nfse['received_xml'])
            self.env.cr.commit()
            if "CompNfse" in dir(retorno):
                self.state = 'done'
                self.codigo_retorno = '100'
                self.mensagem_retorno = 'NFSe emitida com sucesso'
                self.verify_code = retorno.CompNfse.Nfse.InfNfse.CodigoVerificacao
                self.numero_nfse = retorno.CompNfse.Nfse.InfNfse.Numero
            else:
                mensagem_retorno = retorno.MensagemRetorno[0][0]
                self.codigo_retorno = 'ERR'
                self.mensagem_retorno = '%s' % (mensagem_retorno['Mensagem'])
     
            self.env['invoice.eletronic.event'].create({
                'code': self.codigo_retorno,
                'name': self.mensagem_retorno,
                'invoice_eletronic_id': self.id,
            })
        else:
            self.codigo_retorno = '???'
            self.mensagem_retorno = enviar_nfse['received_xml']
            
    @api.multi
    def action_cancel_document(self, context=None, justificativa=None):
        if self.model not in ('041'):
            return super(InvoiceEletronic, self).action_cancel_document(justificativa=justificativa)

#         if not justificativa:
#             return {
#                 'name': 'Cancelamento NFe',
#                 'type': 'ir.actions.act_window',
#                 'res_model': 'wizard.cancel.nfse',
#                 'view_type': 'form',
#                 'view_mode': 'form',
#                 'target': 'new',
#                 'context': {
#                     'default_edoc_id': self.id
#                 }
#             }
#         cert = self.company_id.with_context({'bin_size': False}).nfe_a1_file
#         cert_pfx = base64.decodestring(cert)
#         certificado = Certificado(cert_pfx, self.company_id.nfe_a1_password)
# 
#         company = self.company_id
#         city_prestador = self.company_id.partner_id.city_id
#         canc = {
#             'cnpj_prestador': re.sub('[^0-9]', '', company.cnpj_cpf),
#             'inscricao_municipal': re.sub('[^0-9]', '', company.inscr_mun),
#             'cidade': '%s%s' % (city_prestador.state_id.ibge_code,
#                                 city_prestador.ibge_code),
#             'numero_nfse': self.numero_nfse,
#             'codigo_cancelamento': '1',  # Erro na emissão
#         }
#         cancel = cancelar_nfse(certificado, cancelamento=canc, ambiente=self.ambiente)
# 
#         retorno = cancel['object']
#         if "Cancelamento" in dir(retorno):
#             self.state = 'cancel'
#             self.codigo_retorno = '100'
#             self.mensagem_retorno = 'Nota Fiscal de Serviço Cancelada'
#         else:
#             # E79 - Nota já está cancelada
#             if retorno.ListaMensagemRetorno.MensagemRetorno.Codigo != 'E79':
#                 mensagem = "%s - %s" % (
#                     retorno.ListaMensagemRetorno.MensagemRetorno.Codigo,
#                     retorno.ListaMensagemRetorno.MensagemRetorno.Mensagem
#                 )
#                 raise UserError(mensagem)
# 
#             self.state = 'cancel'
#             self.codigo_retorno = '100'
#             self.mensagem_retorno = 'Nota Fiscal de Serviço Cancelada'
# 
#         self.env['invoice.eletronic.event'].create({
#             'code': self.codigo_retorno,
#             'name': self.mensagem_retorno,
#             'invoice_eletronic_id': self.id,
#         })
#         self._create_attachment('canc', self, cancel['sent_xml'])
#         self._create_attachment('canc-ret', self, cancel['received_xml'])
