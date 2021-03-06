# © 2019 Danimar Ribeiro <danimaribeiro@gmail.com>, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ProductUom(models.Model):
    _inherit = 'product.uom'
    _order = 'display_name'


    display_name = fields.Char(compute='_compute_display_name', store=True, index=True)
    l10n_br_description = fields.Char(string="Description", size=60, index=True)

    @api.depends('name', 'l10n_br_description')
    def _compute_display_name(self):
        for uom in self:
            uom.display_name = uom.name
#             if not uom.l10n_br_description:
#                 uom.display_name = uom.name
#             else:
#                 uom.display_name = uom.l10n_br_description

    def write(self, values):
        # Users can not update the factor if open stock moves are based on it
        if 'factor' in values or 'factor_inv' in values or 'category_id' in values:
            changed = self.filtered(
                lambda u: any(u[f] != values[f] if f in values else False
                              for f in {'factor', 'factor_inv'})) + self.filtered(
                lambda u: any(u[f].id != int(values[f]) if f in values else False
                              for f in {'category_id'}))
            if changed:
                stock_move_lines = self.env['stock.move.line'].search_count([
                    ('product_uom_id.category_id', 'in', changed.mapped('category_id.id')),
                    ('state', '!=', 'cancel'),
                ])

                if stock_move_lines:
                    raise UserError(_(
                        "You cannot change the ratio of this unit of mesure as some"
                        " products with this UoM have already been moved or are "
                        "currently reserved."
                    ))
        return super(ProductUom, self).write(values)

    @api.multi
    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, "%s - %s" % (rec.name, rec.l10n_br_description or '')))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            # Be sure name_search is symetric to name_get
            name = name.split(' / ')[-1]
            args = ['|',('name', operator, name),('l10n_br_description', operator, name)] + args
        return self.search(args, limit=limit).name_get()


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_br_sped_type = fields.Selection(
        [('00', '00 - Mercadoria para Revenda'),
         ('01', '01 - Matéria Prima'),
         ('02', '02 - Embalagem'),
         ('03', '03 - Produto em Processo'),
         ('04', '04 - Produto Acabado'),
         ('05', '05 - Subproduto'),
         ('06', '06 - Produto Intermediário'),
         ('07', '07 - Material de uso e consumo'),
         ('08', '08 - Ativo Imobilizado'),
         ('09', '09 - Serviços'),
         ('10', '10 - Outros insumos'),
         ('99', '99 - Outras')], string="SPED Type", default=0)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    _sql_constraints = [
        ('default_code_uniq', 'unique (default_code)',
         _('Product Reference must be unique!'))
    ]

    @api.multi
    def write(self, vals):
        for product in self:
            values = {}
            values['product_id'] = product.id
            if 'name' in vals:
                values['name'] = 'name'
                values['old_value'] = product.name
                values['new_value'] = vals.get('name')
                self.env['l10n_br.product.changes'].sudo().create(values)
            if 'default_code' in vals:
                values['name'] = 'default_code'
                values['old_value'] = product.default_code
                values['new_value'] = vals.get('default_code')
                self.env['l10n_br.product.changes'].sudo().create(values)

        return super(ProductProduct, self).write(vals)


class L10nBrProductChanges(models.Model):
    _name = "l10n_br.product.changes"
    _description = """Alteração no produto"""

    product_id = fields.Many2one('product.product', 'Product')
    name = fields.Char('Field name', readonly=True, size=30)
    changed_date = fields.Datetime(
        string='Changed Date', default=fields.Datetime.now, readonly=True)
    old_value = fields.Char('Old value', readonly=True)
    new_value = fields.Char('New value', readonly=True)
