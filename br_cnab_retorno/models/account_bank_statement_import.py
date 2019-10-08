# 11.0.0.1 - 06/2019 - Versão Inicial Alexandre Defendi

import logging
#import tempfile

#from decimal import Decimal
from datetime import datetime
from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.addons.base.res.res_bank import sanitize_account_number

_logger = logging.getLogger(__name__)

SUCCESS_CNAB_RETURN = (6, 8, 10, '06', '08', '10',)

class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    def get_move_line_domain(self, evento):
        data_vencimento = str(evento.vencimento_titulo).zfill(8)
        data_vencimento = '{}-{}-{}'.format(data_vencimento[4:], data_vencimento[2:4], data_vencimento[:2])
 
        domain = [
            ('name', 'like', evento.numero_documento),
            ('nosso_numero', '=', evento.nosso_numero),
            ('date_maturity', '=', data_vencimento)
        ]
 
        if evento.sacado_inscricao_numero:
            partner = self.env['res.partner'].search(
                [('cnpj_cpf', '=', self._format_cnpj_cpf(str(evento.sacado_inscricao_numero)))]
            )
        else:
            partner = self.env['res.partner'].search([('legal_name', 'like', evento.sacado_nome)])
 
        if len(partner) == 1:
            domain.append(('partner_id', '=', partner.id))
 
        return domain

    def _get_bankstatment(self, arquivo, journal_id, CnabRetorno=False):
        transacoes = []
        move_lines = []
        cnab_lines = []
        valor_total = 0.0
        bank_identification = journal_id.bank_id
        
        if CnabRetorno and CnabRetorno.eventos_id:
            for evento in CnabRetorno.eventos_id:
                if not evento.move_id: 
                    if evento.cod_motivo.zfill(2) in SUCCESS_CNAB_RETURN:
                        if not evento.moveline_id:
                            domain = [
                                ('name', 'like', evento.numero_documento),
                                ('nosso_numero', '=', evento.nosso_numero),
                                #('date_maturity', '=', evento.data_vencimento)
                            ]
                            evento.moveline_id = move_line = self.env['account.move.line'].search(domain,limit=1)
                        else:
                            move_line = evento.moveline_id
                            if move_line.full_reconcile_id:
                                evento.state = 'done'
                                evento.note = "Já existe uma reconciliação para este evento!"
                            else:
                                move_lines.append(move_line)
                                evento.moveline_id = move_line.id
                                transacoes.append({
                                    'name': "%s : %s" % (
                                        move_line.partner_id.name or evento.sacado_nome,
                                        evento.numero_documento or "%s: %s" % (
                                            move_line.move_id.name, move_line.name)),
                                    'date': datetime.strptime(str(move_line.date), '%Y-%m-%d'),
                                    'amount': evento.valor,
                                    'partner_name': move_line.partner_id.name or evento.sacado_nome,
                                    'partner_id': move_line.partner_id.id,
                                    'ref': evento.numero_documento,
                                    'unique_import_id': str(evento.nosso_numero),
                                    'nosso_numero': evento.nosso_numero,
                                    'cnab_id': evento.id,
                                })
                                evento.state = 'fail'
                                evento.note = "Falha ao reconciliar, favor verifique."
                    else:
                        evento.state = 'none'
                elif not evento.cod_motivo.zfill(2) in SUCCESS_CNAB_RETURN:
                    if evento.statementline_id:
                        evento.cancel_cnab()
                    evento.state = 'none'
                    
        else:
            for lote in arquivo.lotes:
                for evento in lote.eventos:
                    # Apenas liquidação  (Sicoob:6)
                    # Liquidação Banco do Brasil (6, 17)
                    # Liquidação Bradesco (6, 177)
                    # Liquidação Santander ('06', '17')
                    nosso_numero = self._get_nosso_numero(bank_identification.bic, evento.nosso_numero)
                    valor = float(evento.valor_titulo)
                    data_vencimento = str(evento.vencimento_titulo).zfill(8)
                    data_vencimento = '{0}-{1}-{2}'.format(data_vencimento[4:], data_vencimento[2:4], data_vencimento[:2]) if data_vencimento != '00000000' else False
                    vals = {
                        'partner_name': evento.sacado_nome,
                        'numero_documento': evento.numero_documento,
                        'nosso_numero': evento.nosso_numero,
                        'cod_motivo': evento.servico_codigo_movimento,
                        'data_vencimento': data_vencimento,
                        'valor': 0,
                        'cnab_retorno_id': self.id,
                        'note': False,
                        'moveline_id': False,
                    }
                    if evento.servico_codigo_movimento in SUCCESS_CNAB_RETURN:
                        vals['valor'] = valor
                        valor_total += valor
    
                        domain = self.get_move_line_domain(evento)
    
                        move_line = self.env['account.move.line'].search(domain)
                        
                        if move_line:   #Verifica já está reconciliado
                            
                            vals['moveline_id'] = move_line.id
                            
                            if move_line.statement_id:
                                vals['state'] = 'fail'
                                vals['note'] = "Já existe uma reconciliação para este evento!"
                            else:
                                move_lines.append(move_line)
                                
                                transacoes.append({
                                    'name': "%s : %s" % (
                                        move_line.partner_id.name or evento.sacado_nome,
                                        evento.numero_documento or "%s: %s" % (
                                            move_line.move_id.name, move_line.name)),
                                    'date': datetime.strptime(
                                        str(evento.data_ocorrencia), '%d%m%Y'),
                                    'amount': valor,
                                    'partner_name':
                                    move_line.partner_id.name or evento.sacado_nome,
                                    'partner_id': move_line.partner_id.id,
                                    'ref': evento.numero_documento,
                                    'unique_import_id': str(evento.nosso_numero),
                                    'nosso_numero': nosso_numero,
                                })
                                vals['state'] = 'fail'
                                vals['note'] = "Falha ao reconciliar, favor verifique."
                        else:
                            vals['state'] = 'fail'
                            vals['note'] = "Documento {name} {nosso_numero} {date_maturity} não localizado!".format(name=evento.numero_documento,
                                                                                                                    nosso_numero=evento.nosso_numero,
                                                                                                                    date_maturity=data_vencimento)
                    else:
                        vals['state'] = 'none'
    
                    cnab_lines.append(vals)

        inicio = final = datetime.now()
        if len(transacoes):
            primeira_transacao = min(transacoes, key=lambda x: x["date"])
            ultima_transacao = max(transacoes, key=lambda x: x["date"])
            inicio = primeira_transacao["date"]
            final = ultima_transacao["date"]
        else:
            return (
                'BRL',
                0,
                [],
                [],
                cnab_lines,
            )

        last_bank_stmt = self.env['account.bank.statement'].search(
            [('journal_id', '=', journal_id.id)],
            order="date desc, id desc", limit=1)
        last_balance = last_bank_stmt and last_bank_stmt[0].balance_end or 0.0

        vals_bank_statement = {
            'name': "%s - %s até %s" % (
                arquivo.header.nome_do_banco,
                inicio.strftime('%d/%m/%Y'),
                final.strftime('%d/%m/%Y')),
            'date': inicio,
            'balance_start': last_balance,
            'balance_end_real': last_balance + valor_total,
            'transactions': transacoes,
            'journal_id': journal_id.id,
        }
        account_number = arquivo.header.cedente_conta or ''
        if self.force_journal_account:
            account_number = self.journal_id.bank_acc_number

        move_lines_data = []
        for line in move_lines:
            move_lines_data.append({
                u'payment_aml_ids': [],
                u'new_aml_dicts': [],
                u'counterpart_aml_dicts': [{
                    u'credit': line.debit,
                    u'counterpart_aml_id': line.id,
                    u'name': str(line.move_id.name) + ': ' + str(line.name),
                    u'debit': 0,
                    u'payment_mode_id': line.payment_mode_id.id,
                    u'nosso_numero': line.nosso_numero}]
            })

        return (
            'BRL',
            account_number,
            [vals_bank_statement],
            move_lines_data,
            cnab_lines,
        )
 
    def _create_statement(self, vals_bank_statement, account_number):
        bank_statement_obj = self.env['account.bank.statement']
        bank_statement_line_obj = self.env['account.bank.statement.line']
        statement_lines = []
        journal_id = self.env.context['journal_id']
        for transaction in vals_bank_statement['transactions']:
            if not transaction.get('unique_import_id') or not bool(
                bank_statement_line_obj.sudo().search(
                    [
                        ('unique_import_id',
                         '=',
                         transaction['unique_import_id'])
                    ],
                    limit=1
                )
            ):
                if transaction['amount'] != 0:
                    sanitized_account_number = sanitize_account_number(
                        str(account_number)
                    )
 
                    transaction['unique_import_id'] = \
                        (
                            sanitized_account_number and
                            sanitized_account_number + '-' or ''
                        ) + str(journal_id.id) + '-' + \
                        transaction['unique_import_id']
 
                    if bank_statement_line_obj.search([('unique_import_id', '=', transaction['unique_import_id'])]):
                        raise Warning('Transações de contas bancárias podem ser importados apenas uma vez !')
 
                    partner_bank = self.env['res.partner.bank'].search([
                        ('acc_number', '=', sanitized_account_number)],
                        limit=1)
 
                    transaction['bank_account_id'] = partner_bank.id
 
                    statement_lines.append(transaction)
        if vals_bank_statement.get('statement_id'):
            vals_bank_statement.pop('transactions', None)
            line_ids = []
            for line in statement_lines:
                line_ids += [(0, 0, line)]
            return vals_bank_statement['statement_id'].write({'line_ids': line_ids})
        else:
            if len(statement_lines) > 0:
                vals_bank_statement.pop('transactions', None)
                vals_bank_statement['line_ids'] = [
                    [0, False, line] for line in statement_lines]
     
            return bank_statement_obj.with_context(
                            {'journal_id': journal_id.id}
                        ).create(vals_bank_statement)

    @api.one
    @api.depends('line_ids.journal_entry_ids')
    def _check_lines_reconciled(self):
        self.all_lines_reconciled = all([line.journal_entry_ids.ids or line.account_id.id for line in self.line_ids])

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'
    
    @api.multi
    def button_cancel_reconciliation(self):
        super(AccountBankStatementLine,self).button_cancel_reconciliation()
        for rec in self:
            cnablines = self.env['cnab.retorno.line'].search([('statementline_id','=',rec.id)])
            for cnabline in cnablines:
                cnabline.state = 'draft' 
 
            
        
        