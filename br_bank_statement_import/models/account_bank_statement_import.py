# © 2016 Danimar Ribeiro, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import io
import re
import logging
import chardet

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.addons.base.res.res_bank import sanitize_account_number

_logger = logging.getLogger(__name__)

try:
    from ofxparse import OfxParser
except ImportError:
    _logger.error('Cannot import ofxparse dependencies.', exc_info=True)

class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    # Ensure transactions can be imported only once (if the import format provides unique transaction ids)
    unique_import_id = fields.Char(string='Import ID', readonly=True, copy=False)

    _sql_constraints = [
        ('unique_import_id', 'unique (unique_import_id,date,amount_currency)', 'A bank account transactions can be imported only once !')
    ]

class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    force_format = fields.Boolean(string=u'Forçar formato', default=False)
    convert_decimal_br = fields.Boolean(string=u'Converte Decimal', default=True)
    file_format = fields.Selection([('ofx', 'Extrato OFX')],
                                   string="Formato do Arquivo",
                                   default='ofx')
    force_journal_account = fields.Boolean(string=u"Forçar conta bancária?")
    journal_id = fields.Many2one('account.journal', string=u"Conta Bancária",
                                 domain=[('type', '=', 'bank')])

    def _parse_file(self, data_file):
        if self.force_format:
            if self.convert_decimal_br:
                encoding = chardet.detect(data_file)['encoding']
                data_file = data_file.decode(encoding)
                decmark_reg = re.compile('(?<=\d),(?=\d)')
                data_file = decmark_reg.sub('.',data_file)
                data_file = data_file.encode(encoding)
            self._check_ofx(data_file, raise_error=True)
            return self._parse_ofx(data_file)
        else:
            if self._check_ofx(data_file):
                return self._parse_ofx(data_file)
            return super(AccountBankStatementImport, self)._parse_file(
                data_file)

    def _check_ofx(self, data_file, raise_error=False):
        try:
            encoding = chardet.detect(data_file)['encoding']
            data_file = data_file.decode(encoding)
            data_file = data_file.replace('\r\n', '\n').replace('\r', '\n')
            data_file = data_file.encode(encoding)
            OfxParser.parse(io.BytesIO(data_file))
            return True
        except Exception as e:
            if raise_error:
                raise UserError(_("Arquivo formato inválido:\n%s") % str(e))
            return False

    def _parse_ofx(self, data_file):
        ofx = OfxParser.parse(io.BytesIO(data_file))
        transacoes = []
        total = 0.0
        for account in ofx.accounts:
            for transacao in account.statement.transactions:
                trans = self.env['account.bank.statement.line'].search([('unique_import_id','=',transacao.id)])
                if len(trans) > 0:
                    for tr in trans:
                        _logger.info(str(tr))
                transacoes.append({
                    'date': transacao.date,
                    'name': transacao.payee + (
                        transacao.memo and ': ' + transacao.memo or ''),
                    'ref': transacao.id,
                    'amount': transacao.amount,
                    'unique_import_id': transacao.id,
                    'sequence': len(transacoes) + 1,
                })
                total += float(transacao.amount)
        # Really? Still using Brazilian Cruzeiros :/
        if ofx.account.statement.currency.upper() == "BRC":
            ofx.account.statement.currency = "BRL"

        journal = self.journal_id
        if not self.force_journal_account:
            dummy, journal = self._find_additional_data(
                ofx.account.statement.currency, ofx.account.number)

        name = u"%s - %s até %s" % (
            journal.name,
            ofx.account.statement.start_date.strftime('%d/%m/%Y'),
            ofx.account.statement.end_date.strftime('%d/%m/%Y')
        )
        total = round(total, 2)
        vals_bank_statement = {
            'name': name,
            'transactions': transacoes,
            'balance_start': round(
                float(ofx.account.statement.balance) - total, 2),
            'balance_end_real': round(ofx.account.statement.balance, 2),
        }

        account_number = ofx.account.number
        if self.force_journal_account:
            account_number = self.journal_id.bank_acc_number
        return (
            ofx.account.statement.currency,
            account_number,
            [vals_bank_statement]
        )

    @api.multi
    def import_file(self):
        res = super(AccountBankStatementImport,self).import_file()
        statment_id = res['context']['statement_ids']
        if len(statment_id)>0:
            statment = self.env['account.bank.statement'].browse(statment_id)[0]
            Vals_atach = {
                'name': self.filename,
                'db_datas': self.data_file,
                'datas_fname': self.filename,
                'res_model': statment._name,
                'res_id': statment.id,
                'description': 'Arquivo OFX {} '.format(statment.name),
                'type': 'binary',
            }
            self.env['ir.attachment'].sudo().create(Vals_atach)
        return res

    def _create_bank_statements(self, stmts_vals):
        """ Create new bank statements from imported values, filtering out already imported transactions, and returns data used by the reconciliation widget """
        BankStatement = self.env['account.bank.statement']
        BankStatementLine = self.env['account.bank.statement.line']

        # Filter out already imported transactions and create statements
        statement_ids = []
        ignored_statement_lines_import_ids = []
        for st_vals in stmts_vals:
            filtered_st_lines = []
            for line_vals in st_vals['transactions']:
                if 'unique_import_id' not in line_vals \
                   or not line_vals['unique_import_id'] \
                   or not bool(BankStatementLine.sudo().search([
                       ('unique_import_id', '=', line_vals['unique_import_id']),
                       ('date','=',line_vals['date']),
                       ('amount','=',line_vals['amount']),
                       ], limit=1)):
                    filtered_st_lines.append(line_vals)
                else:
                    ignored_statement_lines_import_ids.append(line_vals['unique_import_id'])
                    if 'balance_start' in st_vals:
                        st_vals['balance_start'] += float(line_vals['amount'])

            if len(filtered_st_lines) > 0:
                # Remove values that won't be used to create records
                st_vals.pop('transactions', None)
                for line_vals in filtered_st_lines:
                    line_vals.pop('account_number', None)
                # Create the satement
                st_vals['line_ids'] = [[0, False, line] for line in filtered_st_lines]
                statement_ids.append(BankStatement.create(st_vals).id)
        if len(statement_ids) == 0:
            raise UserError(_('You have already imported that file.'))

        # Prepare import feedback
        notifications = []
        num_ignored = len(ignored_statement_lines_import_ids)
        if num_ignored > 0:
            notifications += [{
                'type': 'warning',
                'message': _("%d transactions had already been imported and were ignored.") % num_ignored if num_ignored > 1 else _("1 transaction had already been imported and was ignored."),
                'details': {
                    'name': _('Already imported items'),
                    'model': 'account.bank.statement.line',
                    'ids': BankStatementLine.search([('unique_import_id', 'in', ignored_statement_lines_import_ids)]).ids
                }
            }]
        return statement_ids, notifications

    def _check_journal_bank_account(self, journal, account_number):
        if not self.force_journal_account:
            return bool(journal.bank_account_id.sanitized_acc_number == account_number)
        else:
            return True
