# © 2016 Alessandro Fernandes Martini, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
import tempfile
import csv
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ProductFiscalClassificationWizard(models.TransientModel):
    _name = 'product.fiscal.classification.wizard'

    product_fiscal_class_csv = fields.Binary(string="Arquivo CSV")
    ncm_csv_delimiter = fields.Char(string='Delimitador', size=3,
                                    required=True)
    has_quote_char = fields.Boolean(string=u'Possui caracter de citação?')
    ncm_quote_char = fields.Char(string=u'Caracter de Citação', size=3)

    @api.multi
    def _verifica_arquivo(self,lines):
        error = []
        if not 'codigo' in lines.fieldnames:
            error.append('codigo')
        if not 'nacionalfederal' in lines.fieldnames:
            error.append('nacionalfederal')
        if not 'importadosfederal' in lines.fieldnames:
            error.append('importadosfederal')
        if not 'estadual' in lines.fieldnames:
            error.append('estadual')
        if not 'municipal' in lines.fieldnames:
            error.append('municipal')
        return error

    @api.multi
    def import_ncm(self):
        if not self.product_fiscal_class_csv:
            raise UserError(_('Nenhum Arquivo Selecionado!'))
        ncm_string = base64.decodestring(self.product_fiscal_class_csv)
        temp = tempfile.NamedTemporaryFile(delete=False)
        temp.write(ncm_string)
        temp.close()
        with open(temp.name, 'r') as csvfile:
            if not self.has_quote_char:
                ncm_lines = csv.DictReader(
                    csvfile, delimiter=str(self.ncm_csv_delimiter))
            else:
                if not self.ncm_quote_char:
                    raise UserError(_('Se o campo indicador de caracter de \
citação estiver marcado é necessário informá-lo!'))
                ncm_lines = csv.DictReader(
                    csvfile, delimiter=str(self.ncm_csv_delimiter),
                    quotechar=self.ncm_quote_char)
            erros = self._verifica_arquivo(ncm_lines)
            if len(erros) > 0:
                msg = 'Não localizamos os seguintes campos:\n'
                for er in erros:
                    msg += er + '\n'
                msg += 'Constam os seguintes campos no arquivo:'
                for cp in ncm_lines.fieldnames:
                    msg += cp + '\n'
                raise UserError(msg)
            for line in ncm_lines:
                code = line['codigo']
                ncm_tax = {
                    'federal_nacional': float(line['nacionalfederal']),
                    'federal_importado': float(line['importadosfederal']),
                    'estadual_imposto': float(line['estadual']),
                    'municipal_imposto': float(line['municipal']), }
                if len(code.zfill(4)) == 4:
                    try:
                        code = code.zfill(4)
                        code = code[:2] + '.' + code[2:]
                        service = self.env['br_account.service.type'].search(
                            [('code', '=', code)])
                        service.update(ncm_tax)
                    except Exception as e:
                        _logger.error(e.message, exc_info=True)
                elif len(code.zfill(8)) == 8:
                    code = code.zfill(8)
                    try:
                        service = self.env['product.fiscal.classification'].\
                            search([('code', '=', code)])
                        service.update(ncm_tax)
                    except Exception as e:
                        _logger.error(e.message, exc_info=True)
        return {  # Recarrega a view após a importação para mostrar resultados
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
