# -*- coding: utf-8 -*-

import re
import io
import base64
import logging
#import pytz
from lxml import etree
from datetime import datetime, timedelta
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTFT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT

_logger = logging.getLogger(__name__)

try:
#     from pytrustnfe.nfe import autorizar_nfe
#     from pytrustnfe.nfe import xml_autorizar_nfe
#     from pytrustnfe.nfe import retorno_autorizar_nfe
#     from pytrustnfe.nfe import recepcao_evento_cancelamento
#     from pytrustnfe.nfe import consultar_protocolo_nfe
#     from pytrustnfe.certificado import Certificado
#     from pytrustnfe.utils import ChaveNFe, gerar_chave, gerar_nfeproc, \
#         gerar_nfeproc_cancel
    from pytrustnfe.nfe.danfce import danfce
#     from pytrustnfe.xml.validate import valida_nfe
except ImportError:
    _logger.info('Cannot import pytrustnfe', exc_info=True)

STATE = {'edit': [('readonly', False)]}


class InvoiceEletronic(models.Model):
    _inherit = 'invoice.eletronic'

    cnpj_cpf = fields.Char('CNPJ/CPF', size=18, copy=False, readonly=True, states=STATE)
    nome = fields.Char('Nome', size=100, copy=False, readonly=True, states=STATE)
    email = fields.Char('E-Mail', size=100, copy=False, readonly=True, states=STATE)
    qrcode = fields.Text('QRCode', copy=False, readonly=True, states=STATE)
 
    @api.multi
    def _hook_validation(self):
        errors = super(InvoiceEletronic, self)._hook_validation()
        if self.model == '65':
            if not self.env.user.company_id.csc:
                errors.append(u'Emitente / Indique o código do identificador CSC')
        return errors
    
    @api.multi
    def _prepare_eletronic_invoice_values(self):
        res = super(InvoiceEletronic, self)._prepare_eletronic_invoice_values()
        if self.model != '65':
            return res
        
        codigo_seguranca = {
            'csc': self.env.user.company_id.csc,
            'cid_token': self.env.user.company_id.id_token_csc, #ebora envie o cid, mas ele não está sendo tratado na PyTrustNFe
        }
        
        res['codigo_seguranca'] = codigo_seguranca
        
        if res.get('compra',False):
            del res['compra']

        if res.get('dest',False):
            del res['dest']

        if bool(self.cnpj_cpf):
            cnpj_cpf = re.sub('[^0-9]', '', self.cnpj_cpf or '')
            dest = {}
            if len(cnpj_cpf) == 11:
                dest.update({
                    'tipo': 'person',
                    'cnpj_cpf': cnpj_cpf,
                    'xNome': self.nome if self.nome else '',
                    'indIEDest': '9'
                })
            elif len(cnpj_cpf) == 14:
                dest.update({
                    'tipo': 'company',
                    'cnpj_cpf': cnpj_cpf,
                    'xNome': self.nome if self.nome else '',
                    'indIEDest': '9'
                })
            if len(dest):
                res['dest'] = dest
                if self.ambiente == 'homologacao':
                    res['dest']['xNome'] = 'NF-E EMITIDA EM AMBIENTE DE HOMOLOGACAO - SEM VALOR FISCAL'
        

        if int(self.tipo_emissao) != 1:
            dt_contigencia = datetime.strptime(self.data_fatura, DTFT)
            res['ide']['xJust'] = 'Serviço fora do ar ou inacessivel'
            res['ide']['dhCont'] = dt_contigencia.strftime('%Y-%m-%dT%H:%M:%S-00:00')
            res['ide']['dhSaiEnt'] = dt_contigencia.strftime('%Y-%m-%dT%H:%M:%S-00:00')
            res['ide']['dhEmi'] = dt_contigencia.strftime('%Y-%m-%dT%H:%M:%S-00:00')

        return res

    @api.multi
    def action_issue_contingency(self):
        for nfce in self:
            if nfce.model == '65':
                nfce.write({
                    'state': 'draft',
                    'tipo_emissao': '9',
                    'xml_to_send_name': False,
                    'xml_to_send': False,
                    'qrcode': False,
                })
                nfce.action_post_validate()

    @api.multi
    def action_post_validate(self):
        super(InvoiceEletronic, self).action_post_validate()
        if self.model == '65' and self.xml_to_send:
            xml = base64.decodestring(self.xml_to_send)
            xml = etree.fromstring(xml)
            qrcode = xml.find(".//{http://www.portalfiscal.inf.br/nfe}qrCode")
            if qrcode != None:
                self.qrcode = qrcode.text
            else:
                self.qrcode = "Não encontrado o QRCode no XML"

    @api.multi
    def send_email_nfe(self):
        if self.model not in ('65'):
            super(InvoiceEletronic, self).send_email_nfe()
        else:
            if not self.email:
                raise UserError('Esse documento não possui e-mail cadastrado.')
            mail = self.env.user.company_id.nfe_email_template
            if not mail:
                raise UserError('Modelo de email padrão não configurado')
            atts = self._find_attachment_ids_email()
            values = {
                "attachment_ids": atts + mail.attachment_ids.ids,
                "email_to": self.email,
                "partner_ids": False,
            }
            mail.send_mail(self.invoice_id.id, email_values=values, force_send=True)
            self.email_sent = True
            
    def _find_attachment_ids_email(self):
        atts = super(InvoiceEletronic, self)._find_attachment_ids_email()
        if self.model not in ('65'):
            return atts

        attachment_obj = self.env['ir.attachment']
        nfe_xml = base64.decodestring(self.nfe_processada)
        logo = base64.decodestring(self.invoice_id.company_id.logo)

        tmpLogo = io.BytesIO()
        tmpLogo.write(logo)
        tmpLogo.seek(0)

        xml_element = etree.fromstring(nfe_xml)
        oDanfe = danfce(list_xml=[xml_element], logo=tmpLogo)

        tmpDanfe = io.BytesIO()
        oDanfe.writeto_pdf(tmpDanfe)

        if danfce:
            danfe_id = attachment_obj.create(dict(
                name="Danfce-%08d.pdf" % self.numero,
                datas_fname="Danfce-%08d.pdf" % self.numero,
                datas=base64.b64encode(tmpDanfe.getvalue()),
                mimetype='application/pdf',
                res_model='account.invoice',
                res_id=self.invoice_id.id,
            ))
            atts.append(danfe_id.id)
        return atts

    @api.multi
    def cron_send_nfce(self):
        pass
#         inv_obj = self.env['invoice.eletronic']
#         nfecs = inv_obj.search([('state', '=', 'done'),('model','=','65'),('email_sent','=',False),('email','!=',False)])
#         for item in nfecs:
#             try:
#                 item.send_email_nfe()
#             except Exception as e:
#                 item.log_exception(e)
#                 item.notify_user()

        