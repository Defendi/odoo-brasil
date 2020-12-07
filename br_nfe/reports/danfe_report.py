# © 2017 Danimar Ribeiro, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import pytz
import base64
import logging
from lxml import etree
from io import BytesIO
from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from pytrustnfe.nfe.danfe import danfe
    from pytrustnfe.nfe.danfe import danfe
    from pytrustnfe.nfe.danfce import danfce
    from pytrustnfe.nfe.danfe_simplificado import danfe_simplificado
except ImportError:
    _logger.error('Cannot import pytrustnfe', exc_info=True)


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    def render_qweb_html(self, res_ids, data=None):
        if self.report_name in ['br_nfe.main_template_br_nfe_danfe', 'br_nfe.main_template_br_nfe_danfe_simple']:
            return
        return super(IrActionsReport, self).render_qweb_html(res_ids, data=data)

    def render_qweb_pdf(self, res_ids, data=None):
        if self.report_name not in ['br_nfe.main_template_br_nfe_danfe', 'br_nfe.main_template_br_nfe_danfe_simple']:
            return super(IrActionsReport, self).render_qweb_pdf(res_ids, data=data)

        nfes = self.env['invoice.eletronic'].search([('id', 'in', res_ids)])

        xml_element = []
        cce_xml_element = []
        for nfe in nfes:
            nfe_xml = base64.decodestring(nfe.nfe_processada or nfe.xml_to_send)
            xml_element.append(etree.fromstring(nfe_xml))
            
            cce_list = self.env['ir.attachment'].search([
                ('res_model', '=', 'invoice.eletronic'),
                ('res_id', '=', nfe.id),
                ('name', 'like', 'cce-')
            ])

            if cce_list:
                for cce in cce_list:
                    if len(cce.datas) > 0:
                        cce_xml = base64.decodestring(cce.datas)
                        cce_xml_element.append(etree.fromstring(cce_xml))
                    else:
                        _logger.error("O XML da carta de correção está zerado ou é inválido.", exc_info=True)
            else:
                cce_xml_element = None
                
        logo = False
        if nfe.invoice_id.company_id.logo:
            logo = base64.decodestring(nfe.invoice_id.company_id.logo)
        elif nfe.invoice_id.company_id.logo_web:
            logo = base64.decodestring(nfe.invoice_id.company_id.logo_web)

        if logo:
            tmpLogo = BytesIO()
            tmpLogo.write(logo)
            tmpLogo.seek(0)
        else:
            tmpLogo = False

        timezone = pytz.timezone(self.env.context.get('tz')) or pytz.utc

        
        if nfe.model == '55':
            rascunho = True if not nfe.data_autorizacao and nfe.state != 'done' else False
            if self.report_name == 'br_nfe.main_template_br_nfe_danfe':
                oDanfe = danfe(list_xml=xml_element, logo=tmpLogo,cce_xml=cce_xml_element, timezone=timezone, rascunho=rascunho)
            else:
                oDanfe = danfe_simplificado(list_xml=xml_element, logo=tmpLogo,cce_xml=cce_xml_element, timezone=timezone, rascunho=rascunho)
                
        elif nfe.model == '65':
            oDanfe = danfce(list_xml=[xml_element], logo=tmpLogo)
        
        else:
            raise UserError('Nenhum documento a ser emitido!')

        tmpDanfe = BytesIO()
        oDanfe.writeto_pdf(tmpDanfe)
        danfe_file = tmpDanfe.getvalue()
        tmpDanfe.close()

        return danfe_file, 'pdf'
