from odoo import http
from odoo.http import request
from odoo.tools.translate import _
from odoo.addons.portal.controllers.portal import get_records_pager, pager as portal_pager, CustomerPortal
from odoo.osv.expression import OR
from odoo.exceptions import AccessError
from odoo.tools import consteq

class AttachmentsPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(AttachmentsPortal, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id

        if partner.commercial_partner_id:
            domain = ['|', ('partner_id', '=', partner.id), ('partner_id', '=', partner.commercial_partner_id.id)]
        else:
            domain = [('partner_id', '=', partner.id)]
        domain += [('state','in',['sent','processed']),('type','=','receivable')]
        values['bank_slips_count'] = request.env['payment.order.line'].sudo().search_count(domain)
        return values

    def _bank_slip_check_access(self, bank_slip_id, access_token=None):
        bank_slip = request.env['payment.order.line'].browse([bank_slip_id])
        bank_slip_sudo = bank_slip.sudo()
#         try:
#             bank_slip.check_access_rights('read')
#             bank_slip.check_access_rule('read')
#         except AccessError:
#             if not access_token or not consteq(bank_slip_sudo.access_token, access_token):
#                 raise
        return bank_slip_sudo

    @http.route(['/my/bank_slips', '/my/bank_slips/page/<int:page>'], type='http', auth="user", website=True)
    def my_bank_slips(self, page=1, search=None, **kw):
        user = request.env.user
        if user:
            values = self._prepare_portal_layout_values()
            partner = request.env.user.partner_id

            if partner.commercial_partner_id:
                domain = ['|', ('partner_id', '=', partner.id), ('partner_id', '=', partner.commercial_partner_id.id)]
            else:
                domain = [('partner_id', '=', partner.id)]
            domain += [('state','in',['sent','processed']),('type','=','receivable')]

            # page
            atts_count = request.env['payment.order.line'].sudo().search_count(domain)
            pager = portal_pager(
                url="my/bank_slips",
                url_args={},
                total=atts_count,
                page=page,
                step=self._items_per_page
            )
            
            atts = request.env['payment.order.line'].sudo().search(domain, order='date_maturity desc', limit=self._items_per_page, offset=pager['offset'])
            request.session['my_bank_slips_history'] = atts.ids[:100]
            
            values.update({
                'bank_slips': atts,
                'bank_slips_count': atts_count,
                'page_name': 'bank_slips',
                'default_url': 'my/bank_slips',
                'pager': pager,
            })
            return request.render("br_boleto.portal_my_bank_slips", values)

    @http.route(['/my/bank_slips/pdf/<int:bank_slip_id>'], type='http', auth="public", website=True)
    def portal_my_bank_slip_report(self, bank_slip_id, access_token=None, **kw):
        try:
            bank_slip_sudo = self._bank_slip_check_access(bank_slip_id, access_token)
            move_line = bank_slip_sudo.move_line_id
        except AccessError:
            return request.redirect('/my')

        # print report as sudo, since it require access to taxes, payment term, ... and portal
        # does not have those access rights.
        pdf = request.env.ref('br_boleto.action_boleto_account_move_line').sudo().render_qweb_pdf([move_line.id])[0]
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)


