from odoo import api, fields, models, _

class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    @api.model
    def get_fiscal_position(self, partner_id, delivery_id=None, type_inv='out_invoice'):
        if not partner_id:
            return False
        # This can be easily overriden to apply more complex fiscal rules
        PartnerObj = self.env['res.partner']
        partner = PartnerObj.browse(partner_id)

        # if no delivery use invoicing
        if delivery_id:
            delivery = PartnerObj.browse(delivery_id)
        else:
            delivery = partner

        if type_inv in ('out_invoice','in_refund'):
            # partner manually set fiscal position always win
            if delivery.property_account_position_id or partner.property_account_position_id:
                return delivery.property_account_position_id.id or partner.property_account_position_id.id
        else:
            # partner manually set fiscal position always win
            if delivery.property_purchase_fiscal_position_id or partner.property_purchase_fiscal_position_id:
                return delivery.property_purchase_fiscal_position_id.id or partner.property_purchase_fiscal_position_id.id

        # First search only matching VAT positions
        fp = self._get_fpos_by_region(delivery.country_id.id, delivery.state_id.id, delivery.zip, False)

        return fp.id if fp else False
