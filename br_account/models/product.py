import babel
import copy
import datetime
import dateutil.relativedelta as relativedelta
import logging
import functools
from werkzeug import urls

from odoo import models, fields, api, tools
from odoo.exceptions import UserError
from odoo.tools import pycompat
from .cst import ORIGEM_PROD

_logger = logging.getLogger(__name__)

def format_date(env, date, pattern=False):
    if not date:
        return ''
    try:
        return tools.format_date(env, date, date_format=pattern)
    except babel.core.UnknownLocaleError:
        return date

def format_amount(env, amount, currency):
    fmt = "%.{0}f".format(currency.decimal_places)
    lang = env['res.lang']._lang_get(env.context.get('lang') or 'en_US')

    formatted_amount = lang.format(fmt, currency.round(amount), grouping=True, monetary=True)\
        .replace(r' ', u'\N{NO-BREAK SPACE}').replace(r'-', u'-\N{ZERO WIDTH NO-BREAK SPACE}')

    pre = post = u''
    if currency.position == 'before':
        pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=currency.symbol or '')
    else:
        post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=currency.symbol or '')

    return u'{pre}{0}{post}'.format(formatted_amount, pre=pre, post=post)

try:
    # We use a jinja2 sandboxed environment to render mako templates.
    # Note that the rendering does not cover all the mako syntax, in particular
    # arbitrary Python statements are not accepted, and not all expressions are
    # allowed: only "public" attributes (not starting with '_') of objects may
    # be accessed.
    # This is done on purpose: it prevents incidental or malicious execution of
    # Python code that may break the security of the server.
    from jinja2.sandbox import SandboxedEnvironment
    mako_template_env = SandboxedEnvironment(
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="${",
        variable_end_string="}",
        comment_start_string="<%doc>",
        comment_end_string="</%doc>",
        line_statement_prefix="%",
        line_comment_prefix="##",
        trim_blocks=True,               # do not output newline after blocks
        autoescape=True,                # XML/HTML automatic escaping
    )
    mako_template_env.globals.update({
        'str': str,
        'quote': urls.url_quote,
        'urlencode': urls.url_encode,
        'datetime': datetime,
        'len': len,
        'abs': abs,
        'min': min,
        'max': max,
        'sum': sum,
        'filter': filter,
        'reduce': functools.reduce,
        'map': map,
        'round': round,

        # dateutil.relativedelta is an old-style class and cannot be directly
        # instanciated wihtin a jinja2 expression, so a lambda "proxy" is
        # is needed, apparently.
        'relativedelta': lambda *a, **kw : relativedelta.relativedelta(*a, **kw),
    })
    mako_safe_template_env = copy.copy(mako_template_env)
    mako_safe_template_env.autoescape = False
except ImportError:
    _logger.warning("jinja2 not available, templating features will not work!")

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    fiscal_type = fields.Selection(
        [('service', 'Serviço'), ('product', 'Produto')], 'Tipo Fiscal',
        required=True, default='product')

    origin = fields.Selection(ORIGEM_PROD, 'Origem', default='0')
    fiscal_classification_id = fields.Many2one(
        'product.fiscal.classification', string="Classificação Fiscal (NCM)")
    service_type_id = fields.Many2one(
        'br_account.service.type', 'Tipo de Serviço')
    cest = fields.Char(string="CEST", size=10,
                       help="Código Especificador da Substituição Tributária")
    fiscal_observation_ids = fields.Many2many(
        'br_account.fiscal.observation', string="Mensagens Doc. Eletrônico")
    fiscal_category_id = fields.Many2one(
        'br_account.fiscal.category',
        string='Categoria Fiscal')
    description_fiscal = fields.Text(
        'Fiscal Description', translate=True,
        help="Descrição do produto a ser inserido nas Faturas. ")

    @api.onchange('type')
    def onchange_product_type(self):
        self.fiscal_type = 'service' if self.type == 'service' else 'product'

    @api.onchange('fiscal_type')
    def onchange_product_fiscal_type(self):
        self.type = 'service' if self.fiscal_type == 'service' else 'consu'

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def render_template(self, template_txt, invoice=False, line=False):

        if isinstance(invoice, pycompat.integer_types):
            invoice = self.env['account.invoice'].browse([invoice])
        if isinstance(line, pycompat.integer_types):
            line = self.env['account.invoice.line'].browse([line])
        
        try:
            mako_env = mako_safe_template_env if self.env.context.get('safe') else mako_template_env
            template = mako_env.from_string(tools.ustr(template_txt))
        except Exception:
            _logger.info("Failed to load template %r", template_txt, exc_info=True)
            return template_txt

        variables = {
            'format_date': lambda date, format=False, context=self._context: format_date(self.env, date, format),
            'format_amount': lambda amount, currency, context=self._context: format_amount(self.env, amount, currency),
            'user': self.env.user,
            'ctx': self._context,  # context kw would clash with mako internals
        }
        
        variables['product'] = self
        
        if bool(invoice):
            variables['invoice'] = invoice
        if bool(line):
            variables['line'] = line
        
        try:
            render_result = template.render(variables)
        except Exception:
            _logger.info("Failed to render template %r using values %r" % (template, variables), exc_info=True)
            raise UserError(_("Failed to render template %r using values %r")% (template, variables))
        
        if render_result == "False":
            render_result = ""
            
        return render_result

    def render_description(self):
        for prod in self:
            prod.description = prod.render_template(prod.description_fiscal,invoice=16754)
