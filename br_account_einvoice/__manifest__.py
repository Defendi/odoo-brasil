# © 2016 Danimar Ribeiro <danimaribeiro@gmail.com>, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{  # pylint: disable=C8101,C8103
    'name': 'Account E-Invoice',
    'summary': """Base Module for the Brazilian Invoice Eletronic""",
    'description': """Base Module for the Brazilian Invoice Eletronic""",
    'version': '11.0.1.0.0',
    'category': 'account',
    'author': 'Trustcode',
    'license': 'AGPL-3',
    'website': 'http://www.trustcode.com.br',
    'contributors': [
        'Danimar Ribeiro <danimaribeiro@gmail.com>',
        'Mackilem Van der Laan <mack.vdl@gmail.com>',
    ],
    'depends': [
        'document',
        'br_base',
        'br_account',
        'br_data_account',
    ],
    'data': [
        'data/nfe_cron.xml',
        'data/br_account_einvoice.xml',
        'views/invoice_eletronic.xml',
        'views/account_invoice.xml',
        'views/account_config_settings.xml',
        'views/res_company.xml',
        'wizard/invoice_eletronic_selection_wizard_view.xml',
        'security/einvoice_security.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True
}
