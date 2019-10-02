import logging

from odoo import fields, models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class AccountMoveLineChangeDateMaturity(models.TransientModel):
    _name = 'account.move.line.change.date.maturity'
    _description = 'Histórico de Mudança na Data de Vencimento'
    
    move_id = fields.Many2one('account.move.line', string="Movimento Contábil", readonly=True, required=True)
    user_id = fields.Many2one('res.users', 'Responsável', default=lambda self: self.env.user)
    can_do = fields.Boolean('Pode fazer', default=False)
    date_maturity = fields.Date(string='De')
    date_maturity_new = fields.Date(string='Para', default=fields.date.today())
    narration = fields.Text('Motivo')
    state = fields.Selection([('draft', 'Aberto'), ('posted', 'Publicado')], string='Status', readonly=True, default='draft')

    @api.onchange('move_id')
    def on_change_move_id(self):
        if self.move_id:
            self.date_maturity = self.move_id.date_maturity
            if self.move_id.account_id.reconcile and not self.move_id.reconciled: 
                self.can_do = True 
            
    def do_new_date_maturity(self):
        if self.can_do:
            if len(self.narration) < 10:
                raise UserError('A narrativa tem que ter mais de 10 caracteres')
            if self.move_id.date_maturity == self.date_maturity_new:
                raise UserError('A nova data tem que ser diferente da data atual')
            self.date_maturity = self.move_id.date_maturity
            self.move_id.write({'date_maturity': self.date_maturity_new})
            self.state = 'posted'
