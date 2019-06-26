# 11.0.0.1 - 06/2019 - Versão Inicial Alexandre Defendi

from odoo import api, fields, models

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.multi
    def reconcile(self, writeoff_acc_id=False, writeoff_journal_id=False):
        res = super(AccountMoveLine, self).reconcile(writeoff_acc_id=writeoff_acc_id, writeoff_journal_id=writeoff_journal_id)
        for rec in self:
            if rec.reconciled:
                for line in rec.full_reconcile_id.reconciled_line_ids:
                    statement_lines = self.env['account.bank.statement.line'].search([('journal_entry_ids','=',line.move_id.id)])
                    if statement_lines:
                        cnablines = self.env['cnab.retorno.line'].search([('statementline_id','in',statement_lines.ids)])
                        for cnabline in cnablines:
                            cnabline.state = 'done' 
        return res