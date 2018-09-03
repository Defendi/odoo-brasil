# -*- coding: utf-8 -*-

# import re
# import io
# import base64
import logging
# import pytz
# from lxml import etree
# from datetime import datetime
from odoo import api, fields, models
from odoo.exceptions import UserError
# from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTFT
# from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT

_logger = logging.getLogger(__name__)

# try:
#     from pytrustnfe.nfe import autorizar_nfe
#     from pytrustnfe.nfe import xml_autorizar_nfe
#     from pytrustnfe.nfe import retorno_autorizar_nfe
#     from pytrustnfe.nfe import recepcao_evento_cancelamento
#     from pytrustnfe.nfe import consultar_protocolo_nfe
#     from pytrustnfe.certificado import Certificado
#     from pytrustnfe.utils import ChaveNFe, gerar_chave, gerar_nfeproc, \
#         gerar_nfeproc_cancel
#     from pytrustnfe.nfe.danfe import danfe
#     from pytrustnfe.xml.validate import valida_nfe
# except ImportError:
#     _logger.info('Cannot import pytrustnfe', exc_info=True)

STATE = {'edit': [('readonly', False)]}


class InvoiceEletronic(models.Model):
    _inherit = 'invoice.eletronic'

    cnpj_cpf = fields.Char('CNPJ/CPF', size=18, copy=False, readonly=True, states=STATE)
    qrcode = fields.Text('QRCode', readonly=True, states=STATE)
    