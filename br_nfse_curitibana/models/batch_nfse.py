import re
import base64

from odoo import api, fields, models
from odoo.exceptions import UserError

from pytrustnfe.xml import sanitize_response

class BatchInvoiceEletronic(models.Model):
    _inherit = 'batch.invoice.eletronic'

    model = fields.Selection(selection_add=[('041', 'Nota Curitibana')])

    def _file_xml(self):
        rps_list = []
        if self.batch_type == 'tonew':
            for nfse in self.document_ids:
                rps_list.append(base64.decodestring(nfse.xml_to_send).decode())
        else:
            for nfse in self.document_cancel_ids:
                rps = {
                    'nfse_number': nfse.numero_nfse,
                    'cnpj_prestador': re.sub('[^0-9]', '',self.company_id.cnpj_cpf or ''),
                    'inscricao_municipal': re.sub('[^0-9]', '',self.company_id.inscr_mun or ''),
                    'cidade': '%s%s' % (self.company_id.state_id.ibge_code,self.company_id.city_id.ibge_code),
                    'cod_cancel': '0',
                }
                rps_list.append(rps)

        if len(rps_list) > 0:
            if self.batch_type == 'tonew':
                lote_value = {
                    'numero_lote': str(self.name),
                    'inscricao_municipal': re.sub('[^0-9]', '',self.company_id.inscr_mun or ''),
                    'cnpj_prestador': re.sub('[^0-9]', '',self.company_id.cnpj_cpf or ''),
                    'lista_rps': rps_list,
                }
                return self.env['invoice.eletronic']._gerar_xml_lote(lote_value,self.company_id.with_context({'bin_size': False}).nfe_a1_file,self.company_id.nfe_a1_password)
            else:
                lote_value = {
                    'inscricao_municipal': re.sub('[^0-9]', '',self.company_id.inscr_mun or ''),
                    'cnpj_prestador': re.sub('[^0-9]', '',self.company_id.cnpj_cpf or ''),
                    'lista_rps': rps_list,
                }
                return self.env['invoice.eletronic']._gerar_xml_cancel_lote(lote_value,self.company_id.with_context({'bin_size': False}).nfe_a1_file,self.company_id.nfe_a1_password)

    @api.multi
    def _create_file(self):
        if self.model != '041':
            super(BatchInvoiceEletronic,self)._create_file(self)
        else:
            if self.format_file == 'xml':
                xml_to_send = self._file_xml()
                if bool(xml_to_send):
                    self.xml_to_send = base64.encodestring(xml_to_send.encode())
                    self.xml_to_send_name = 'nfse-lote-%s.xml' % self.name

    @api.multi
    def _process_return(self):
        if self.model != '041':
            super(BatchInvoiceEletronic,self)._create_file(self)
        else:
            if self.batch_type == 'tonew':
                if bool(self.return_xml):
                    xml_ret = base64.decodestring(self.return_xml).decode()
                    erro = []
                    try:
                        xml_ret, retorno = sanitize_response(xml_ret)
                        if hasattr(retorno, 'ConsultarLoteRpsResult'):
                            list_nfse = retorno.ConsultarLoteRpsResult.ListaNfse.CompNfse.tcCompNfse if hasattr(retorno.ConsultarLoteRpsResult.ListaNfse.CompNfse, 'tcCompNfse') == True else []
                            for NFSe in list_nfse:
                                rps_number = NFSe.Nfse.InfNfse.IdentificacaoRps.Numero.text
                                rps_serie = NFSe.Nfse.InfNfse.IdentificacaoRps.Serie.text
                                Nfse_number = NFSe.Nfse.InfNfse.Numero.text
                                Nfse_code = NFSe.Nfse.InfNfse.CodigoVerificacao.text
                                doc = self.env['invoice.eletronic'].search([('numero','=',rps_number),('serie_documento','=',rps_serie),('model','=',self.model)],limit=1)
                                if len(doc) > 0:
                                    doc.number = Nfse_number
                                    doc.state = 'done'
                                    doc.codigo_retorno = '100'
                                    doc.mensagem_retorno = 'NFSe emitida com sucesso'
                                    doc.verify_code = Nfse_code
                                    doc.numero_nfse = Nfse_number
                                else:
                                    erro += 'Documento NFSe série {} número {}'.format(rps_serie,rps_number)
                        #for message in list_msg_ret:
                        #    erro += message + '\n'
                        if len(erro) > 0:
                            for msg in erro:
                                self.observation += msg
                        else:
                            self.state = 'done'
                    except Exception as e:
                        raise UserError(str(e))
                else:
                    raise UserError('Adicone o arquivo de Retorno')
            else:
                if bool(self.protocolo) and len(self.protocolo) >= 18 and str(self.protocolo).isnumeric():
                    #637243750752384917
                    for doc in self.document_cancel_ids:
                        doc.state = 'cancel'
                        doc.codigo_retorno = '135'
                        doc.mensagem_retorno = 'NFSe cancelada com o protocolo %s' % self.protocolo
                    self.state = 'done'
                else:
                    raise UserError('Número de Protocolo Inválido')
                